from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .services import identify_crop
import base64
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser

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
@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser])  # Limit to multipart to avoid JSON request body inference in Swagger
@csrf_exempt
def identify_view(request):
    if request.method == 'POST':
        # Handle form submission with file
        if request.FILES.get('image'):
            image_file = request.FILES['image']
            try:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                result = identify_crop(image_base64)
                # Check if client accepts JSON (Swagger test) or HTML (Browser)
                if 'application/json' in request.headers.get('Accept', ''):
                     return JsonResponse(result)
                return render(request, 'kindwise/result.html', {'result': result})
            except Exception as e:
                 if 'application/json' in request.headers.get('Accept', ''):
                     return JsonResponse({'error': str(e)}, status=400)
                 return render(request, 'kindwise/upload.html', {'error': str(e)})

    return render(request, 'kindwise/upload.html')
