# DEBUG TEST ENDPOINT for B4_SALES_TARGET troubleshooting
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def debug_test_api(request):
    """Test endpoint to verify debugging is working"""
    print("\n" + "="*80)
    print("🔧 DEBUG TEST ENDPOINT CALLED")
    print(f"🔧 Request URL: {request.get_full_path()}")
    print(f"🔧 Request method: {request.method}")
    print(f"🔧 User: {request.user}")
    print("🔧 If you see this output, debugging is working correctly!")
    print("="*80)

    return Response({
        'success': True,
        'message': 'Debug test successful!',
        'request_url': request.get_full_path(),
        'note': 'Check your server console for debug output'
    })