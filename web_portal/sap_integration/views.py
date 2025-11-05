from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view

from .sap_client import SAPClient
from .models import Policy
from .serializers import PolicySerializer
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import render


# Unified API for Frontend
@swagger_auto_schema(
    method='get',
    operation_description="Get Business Partner data by CardCode - Unified API for Frontend",
    manual_parameters=[
        openapi.Parameter(
            'card_code',
            openapi.IN_PATH,
            description="Business Partner Card Code (e.g., BIC00001)",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={
        200: openapi.Response(
            description="Business Partner data retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "data": {
                        "CardCode": "BIC00001",
                        "CardName": "Sample Business Partner",
                        "CardType": "cCustomer",
                        "CurrentAccountBalance": 15000.50
                    },
                    "message": "Business partner data retrieved successfully"
                }
            }
        ),
        400: openapi.Response(
            description="Invalid card code",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Invalid card code format",
                    "message": "Card code is required"
                }
            }
        ),
        404: openapi.Response(
            description="Business partner not found",
            examples={
                "application/json": {
                    "success": False,
                    "error": "Business partner not found",
                    "message": "No business partner found with the provided card code"
                }
            }
        ),
        500: openapi.Response(
            description="SAP integration error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "SAP integration failed",
                    "message": "Unable to connect to SAP system"
                }
            }
        )
    }
)
@api_view(['GET'])
def get_business_partner_data(request, card_code):
    """
    Unified API endpoint for frontend to get business partner data.
    This endpoint handles all SAP integration internally and returns clean data.
    
    Usage: GET /api/sap/business-partner/{card_code}/
    Example: GET /api/sap/business-partner/BIC00001/
    """
    
    # Validate card_code
    if not card_code or not card_code.strip():
        return Response({
            "success": False,
            "error": "Invalid card code format",
            "message": "Card code is required"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Initialize SAP client
        sap_client = SAPClient()
        
        # Get business partner details with specific fields
        bp_data = sap_client.get_bp_details(card_code.strip())
        
        # Return formatted response for frontend
        return Response({
            "success": True,
            "data": bp_data,
            "message": "Business partner data retrieved successfully"
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        error_message = str(e)
        
        # Handle specific SAP errors
        if "not found" in error_message.lower() or "404" in error_message:
            return Response({
                "success": False,
                "error": "Business partner not found",
                "message": f"No business partner found with card code: {card_code}"
            }, status=status.HTTP_404_NOT_FOUND)
        
        elif "session" in error_message.lower() or "timeout" in error_message.lower():
            return Response({
                "success": False,
                "error": "SAP session error",
                "message": "SAP session expired or invalid. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        else:
            return Response({
                "success": False,
                "error": "SAP integration failed",
                "message": f"Unable to retrieve business partner data: {error_message}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='get',
    operation_description="List all policies from SAP Projects (UDF U_pol)",
    manual_parameters=[
        openapi.Parameter(
            'active',
            openapi.IN_QUERY,
            description="Filter by Active projects (true/false)",
            type=openapi.TYPE_BOOLEAN,
            required=False
        )
    ],
    responses={
        200: openapi.Response(
            description="Policies retrieved successfully",
            examples={
                "application/json": {
                    "success": True,
                    "count": 2,
                    "data": [
                        {
                            "code": "PRJ001",
                            "name": "Example Project",
                            "valid_from": "2024-01-01",
                            "valid_to": "2025-01-01",
                            "active": True,
                            "policy": "POL-123"
                        },
                        {
                            "code": "PRJ002",
                            "name": "Another Project",
                            "valid_from": "2024-02-01",
                            "valid_to": "2025-02-01",
                            "active": False,
                            "policy": "POL-456"
                        }
                    ]
                }
            }
        ),
        500: openapi.Response(
            description="SAP integration error",
            examples={
                "application/json": {
                    "success": False,
                    "error": "SAP integration failed",
                    "message": "Unable to connect to SAP system"
                }
            }
        )
    }
)
@api_view(['GET'])
def list_policies(request):
    """
    API endpoint to list policies from SAP Projects based on UDF `U_pol`.
    Usage: GET /api/sap/policies/
    Optional: ?active=true|false
    """
    try:
        sap_client = SAPClient()
        policies = sap_client.get_all_policies()

        active_param = request.query_params.get('active')
        if active_param is not None:
            active_val = str(active_param).lower() in ('true', '1', 'yes')
            policies = [p for p in policies if bool(p.get('active')) == active_val]

        return Response({
            "success": True,
            "count": len(policies),
            "data": policies,
            "message": "Policies retrieved successfully"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "error": "SAP integration failed",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- Database policy listing (secure API) ---
@swagger_auto_schema(
    method='get',
    operation_description="List policies stored in the database with search and filtering.",
    manual_parameters=[
        openapi.Parameter('search', openapi.IN_QUERY, description="Search code/name/policy", type=openapi.TYPE_STRING),
        openapi.Parameter('active', openapi.IN_QUERY, description="Filter by active true/false", type=openapi.TYPE_BOOLEAN),
        openapi.Parameter('valid_from', openapi.IN_QUERY, description="Filter policies valid on/after this date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        openapi.Parameter('valid_to', openapi.IN_QUERY, description="Filter policies valid on/before this date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
    ]
)
@api_view(['GET'])
def list_db_policies(request):
    qs = Policy.objects.all().order_by('-updated_at')

    search = request.query_params.get('search')
    if search:
        qs = qs.filter(models.Q(code__icontains=search) | models.Q(name__icontains=search) | models.Q(policy__icontains=search))

    active = request.query_params.get('active')
    if active is not None:
        active_val = str(active).lower() in ('true', '1', 'yes')
        qs = qs.filter(active=active_val)

    vf = request.query_params.get('valid_from')
    if vf:
        qs = qs.filter(valid_from__gte=vf)

    vt = request.query_params.get('valid_to')
    if vt:
        qs = qs.filter(valid_to__lte=vt)

    serializer = PolicySerializer(qs, many=True)
    return Response({
        'success': True,
        'count': len(serializer.data),
        'data': serializer.data,
        'message': 'Policies retrieved from database'
    }, status=status.HTTP_200_OK)


# --- Sync from SAP to DB ---
@swagger_auto_schema(
    method='post',
    operation_description="Sync policies from SAP Projects (UDF U_pol) into the database.",
    responses={
        200: openapi.Response(description="Sync completed")
    }
)
@api_view(['POST'])
def sync_policies(request):
    client = SAPClient()
    try:
        rows = client.get_all_policies()
    except Exception as e:
        return Response({
            'success': False,
            'error': 'SAP integration failed',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    import datetime
    def parse_date(val):
        if not val:
            return None
        try:
            if isinstance(val, str):
                return datetime.date.fromisoformat(val.split('T')[0])
            if isinstance(val, datetime.datetime):
                return val.date()
            if isinstance(val, datetime.date):
                return val
        except Exception:
            return None
        return None

    created = 0
    updated = 0
    for row in rows:
        obj, is_created = Policy.objects.update_or_create(
            code=row.get('code'),
            defaults={
                'name': row.get('name') or '',
                'policy': row.get('policy') or '',
                'valid_from': parse_date(row.get('valid_from')),
                'valid_to': parse_date(row.get('valid_to')),
                'active': bool(row.get('active'))
            }
        )
        created += 1 if is_created else 0
        updated += 0 if is_created else 1

    return Response({
        'success': True,
        'created': created,
        'updated': updated,
        'message': 'Policies synced from SAP'
    }, status=status.HTTP_200_OK)


# --- Policy listing page (responsive) ---
@ensure_csrf_cookie
def policy_list_page(request):
    """Render a responsive page to list DB policies with a Sync button."""
    return render(request, 'sap_integration/policies.html')
