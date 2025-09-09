from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.decorators import api_view

from .sap_client import SAPClient


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
