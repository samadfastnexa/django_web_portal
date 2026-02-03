from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .services import identify_crop
from .models import KindwiseIdentification
from .disease_matcher import enrich_kindwise_response
import base64
import json
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser

@swagger_auto_schema(
    method='post',
    operation_description="Identify crop from image (Multipart File Upload). Image will be converted to Base64 server-side.",
    consumes=['multipart/form-data'],
    manual_parameters=[
        openapi.Parameter(
            name="image",
            in_=openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            description="Image file upload",
            required=True
        )
    ],
    # Explicitly set request_body to no_body to prevent drf_yasg from auto-generating it
    # This avoids the "cannot add form parameters when the request has a request body" error
    request_body=no_body,
    responses={
        200: openapi.Response(
            description="Identification results",
            examples={
                "application/json": {
                    "result": {
                        "classification": {
                            "suggestions": [
                                {
                                    "name": "Tomato",
                                    "probability": 0.95,
                                    "similar_images": [{"url": "..."}]
                                }
                            ]
                        }
                    }
                }
            }
        ),
        400: "Bad Request"
    }
)
@swagger_auto_schema(
    method='get',
    operation_description="List identification records for a user.",
    manual_parameters=[
        openapi.Parameter(
            name="user_id",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="User ID to filter records",
            required=True
        )
    ],
    responses={200: openapi.Response(description="List of records")}
)
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser])
@csrf_exempt
def identify_view(request):
    # Feature flag check
    if not getattr(settings, 'KINDWISE_API_ENABLED', True):
        return JsonResponse({'detail': 'Kindwise API is disabled'}, status=503)

    # No client-side API key guard; rely on server-side provider key for upstream calls

    if request.method == 'POST':
        user_id = request.POST.get('user_id') or request.GET.get('user_id')
        if not user_id and request.content_type == 'application/json':
            try:
                body = request.data if isinstance(request.data, dict) else json.loads(request.body.decode('utf-8'))
            except Exception:
                body = {}
            user_id = body.get('user_id')
        # Default to authenticated user if not explicitly provided
        if not user_id and request.user and request.user.is_authenticated:
            user_id = request.user.id

        image_b64 = None
        image_name = None
        # Multipart path
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            image_name = getattr(image_file, 'name', None)
            image_data = image_file.read()
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        # JSON path
        elif request.content_type == 'application/json':
            try:
                body = request.data if isinstance(request.data, dict) else json.loads(request.body.decode('utf-8'))
            except Exception:
                body = {}
            image_b64 = body.get('image_base64') or body.get('image')
        else:
            return JsonResponse({'detail': 'No image provided'}, status=400)

        if image_b64 and isinstance(image_b64, str) and 'base64,' in image_b64:
            try:
                image_b64 = image_b64.split('base64,', 1)[1]
            except Exception:
                pass

        if not image_b64:
            return JsonResponse({'detail': 'Missing image data'}, status=400)

        try:
            result = identify_crop(image_b64)
            status_str = 'error' if isinstance(result, dict) and result.get('error') else 'success'

            # Build request payload snapshot (do not store raw image data)
            request_payload = {
                'has_image': True,
                'user_id': user_id,
            }
            
            # Enrich result with disease recommendations if requested
            include_recommendations = request.GET.get('include_recommendations', 'true').lower() in ['true', '1', 'yes']
            if include_recommendations and status_str == 'success':
                result = enrich_kindwise_response(result, include_recommendations=True)

            # Create record
            record = KindwiseIdentification.objects.create(
                user_id=user_id,
                image_name=image_name,
                request_payload=request_payload,
                response_payload=result,
                status=status_str,
                source_ip=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
            )

            response_data = {
                'id': record.id,
                'status': record.status,
                'created_at': record.created_at,
                'result': result,
            }

            # If client prefers JSON
            if 'application/json' in request.headers.get('Accept', '') or request.content_type == 'application/json':
                return JsonResponse(response_data, safe=False)

            # Otherwise render HTML (optional legacy UI)
            return render(request, 'kindwise/result.html', {'result': result, 'record_id': record.id})
        except Exception as e:
            return JsonResponse({'detail': str(e)}, status=400)

    # GET: list records by user_id
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'detail': 'user_id is required'}, status=400)

    qs = KindwiseIdentification.objects.filter(user_id=user_id).values(
        'id', 'status', 'created_at', 'image_name', 'response_payload'
    )
    return JsonResponse({'count': qs.count(), 'results': list(qs)}, safe=False)


@swagger_auto_schema(
    method='get',
    operation_description="""
    Get all Kindwise identification records or filter by specific user.
    
    - Without user_id: Returns all identification records (Admin use)
    - With user_id: Returns records for specific user only
    
    Results are ordered by most recent first and support pagination.
    """,
    manual_parameters=[
        openapi.Parameter(
            name="user_id",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="User ID to filter records (optional - omit to get all records)",
            required=False
        ),
        openapi.Parameter(
            name="page",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Page number (default: 1)",
            required=False
        ),
        openapi.Parameter(
            name="page_size",
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Number of items per page (default: 10, max: 100)",
            required=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Paginated list of identification records",
            examples={
                "application/json": {
                    "user_id": 5,
                    "user_name": "John Doe",
                    "count": 25,
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 3,
                    "next": "http://localhost:8000/api/kindwise/records/?user_id=1&page=2",
                    "previous": None,
                    "results": [
                        {
                            "id": 10,
                            "status": "success",
                            "created_at": "2024-01-15T10:30:00Z",
                            "image_name": "tomato.jpg",
                            "response_payload": {
                                "classification": {
                                    "suggestions": [
                                        {"name": "Tomato", "probability": 0.95}
                                    ]
                                }
                            }
                        }
                    ]
                }
            }
        ),
        404: "User not found"
    },
    tags=["kindwise"]
)
@api_view(['GET'])
@csrf_exempt
def records_by_user(request):
    """Get all Kindwise identification records or filter by specific user with pagination"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    user_id = request.GET.get('user_id')
    page_number = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)
    
    # Validate and limit page_size
    try:
        page_size = int(page_size)
        page_size = min(max(1, page_size), 100)  # Limit between 1 and 100
    except (ValueError, TypeError):
        page_size = 10
    
    try:
        if user_id:
            # Validate user exists
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(pk=user_id)
                # Handle different user models - some may not have get_full_name
                if hasattr(user, 'get_full_name') and callable(user.get_full_name):
                    user_name = user.get_full_name() or user.username
                elif hasattr(user, 'full_name'):
                    user_name = user.full_name or user.username
                elif hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                    user_name = f"{user.first_name} {user.last_name}".strip() or user.username
                else:
                    user_name = user.username
            except User.DoesNotExist:
                return JsonResponse(
                    {'error': f'User with ID {user_id} not found'},
                    status=404
                )
            
            # Get records for specific user, ordered by most recent first
            qs = KindwiseIdentification.objects.filter(user_id=user_id).order_by('-created_at').values(
                'id', 'status', 'created_at', 'image_name', 'response_payload'
            )
            
            if not qs.exists():
                return JsonResponse({
                    'message': f'No identification records found for user {user_name} (ID: {user_id})',
                    'user_id': int(user_id),
                    'user_name': user_name,
                    'count': 0,
                    'page': 1,
                    'page_size': page_size,
                    'total_pages': 0,
                    'next': None,
                    'previous': None,
                    'results': []
                }, status=200)
            
            # Paginate results
            paginator = Paginator(qs, page_size)
            total_count = paginator.count
            total_pages = paginator.num_pages
            
            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
                page_number = 1
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
                page_number = paginator.num_pages
            
            # Build next and previous URLs
            base_url = request.build_absolute_uri(request.path)
            next_url = None
            previous_url = None
            
            if page_obj.has_next():
                next_url = f"{base_url}?user_id={user_id}&page={page_obj.next_page_number()}&page_size={page_size}"
            
            if page_obj.has_previous():
                previous_url = f"{base_url}?user_id={user_id}&page={page_obj.previous_page_number()}&page_size={page_size}"
            
            return JsonResponse({
                'user_id': int(user_id),
                'user_name': user_name,
                'count': total_count,
                'page': int(page_number),
                'page_size': page_size,
                'total_pages': total_pages,
                'next': next_url,
                'previous': previous_url,
                'results': list(page_obj)
            }, safe=False)
        else:
            # Get all records (no user filter), ordered by most recent first
            qs = KindwiseIdentification.objects.all().order_by('-created_at').values(
                'id', 'user_id', 'status', 'created_at', 'image_name', 'response_payload'
            )
            
            # Paginate results
            paginator = Paginator(qs, page_size)
            total_count = paginator.count
            total_pages = paginator.num_pages
            
            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
                page_number = 1
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
                page_number = paginator.num_pages
            
            # Build next and previous URLs
            base_url = request.build_absolute_uri(request.path)
            next_url = None
            previous_url = None
            
            if page_obj.has_next():
                next_url = f"{base_url}?page={page_obj.next_page_number()}&page_size={page_size}"
            
            if page_obj.has_previous():
                previous_url = f"{base_url}?page={page_obj.previous_page_number()}&page_size={page_size}"
            
            return JsonResponse({
                'message': 'All identification records',
                'count': qs.count(),
                'results': list(qs)
            }, safe=False)
            
    except ValueError:
        return JsonResponse(
            {'error': 'Invalid user ID format. Must be a valid integer.'},
            status=400
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Error retrieving records: {str(e)}'},
            status=500
        )


@swagger_auto_schema(
    method='get',
    operation_description="""
    Get a specific Kindwise identification record by ID.
    
    Returns complete details including:
    - Record ID and status
    - User information
    - Image name
    - Request and response payloads
    - Timestamp and metadata
    """,
    responses={
        200: openapi.Response(
            description="Single identification record",
            examples={
                "application/json": {
                    "id": 10,
                    "user_id": 5,
                    "user_name": "John Doe",
                    "status": "success",
                    "image_name": "tomato.jpg",
                    "created_at": "2024-01-15T10:30:00Z",
                    "source_ip": "192.168.1.1",
                    "request_payload": {"has_image": True, "user_id": 5},
                    "response_payload": {
                        "classification": {
                            "suggestions": [
                                {"name": "Tomato", "probability": 0.95}
                            ]
                        }
                    }
                }
            }
        ),
        404: "Record not found"
    },
    tags=["kindwise"]
)
@api_view(['GET'])
@csrf_exempt
def record_detail(request, record_id):
    """Get a specific Kindwise identification record by ID"""
    try:
        record = KindwiseIdentification.objects.get(pk=record_id)
        
        # Get user information if available
        user_name = None
        if record.user_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(pk=record.user_id)
                
                # Handle different user models
                if hasattr(user, 'get_full_name') and callable(user.get_full_name):
                    user_name = user.get_full_name() or user.username
                elif hasattr(user, 'full_name'):
                    user_name = user.full_name or user.username
                elif hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                    user_name = f"{user.first_name} {user.last_name}".strip() or user.username
                else:
                    user_name = user.username
            except:
                user_name = f"User {record.user_id}"
        
        return JsonResponse({
            'id': record.id,
            'user_id': record.user_id,
            'user_name': user_name,
            'status': record.status,
            'image_name': record.image_name,
            'created_at': record.created_at,
            'source_ip': record.source_ip,
            'user_agent': record.user_agent,
            'request_payload': record.request_payload,
            'response_payload': record.response_payload
        }, safe=False)
        
    except KindwiseIdentification.DoesNotExist:
        return JsonResponse(
            {'error': f'Identification record with ID {record_id} not found'},
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Error retrieving record: {str(e)}'},
            status=500
        )
