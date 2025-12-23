from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .services import identify_crop
from .models import KindwiseIdentification
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
