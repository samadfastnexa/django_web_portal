"""
Custom media file serving with graceful error handling for missing files
"""
from django.http import FileResponse, JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.http import require_http_methods
import os
import mimetypes


@require_http_methods(["GET"])
def serve_media_file(request, path):
    """
    Serve media files with graceful handling of missing files.
    Returns a friendly JSON error message instead of 404 page when file doesn't exist.
    """
    # Construct the full file path, then confirm it stays inside MEDIA_ROOT.
    # realpath collapses any '../' so a traversal like /media/../../.env or
    # /media/../web_portal/settings.py cannot escape the media directory.
    media_root = os.path.realpath(settings.MEDIA_ROOT)
    file_path = os.path.realpath(os.path.join(media_root, path))
    if file_path != media_root and not file_path.startswith(media_root + os.sep):
        return JsonResponse({
            'error': 'Invalid path',
            'message': 'The requested path is not allowed.',
        }, status=403)

    # Check if file exists
    if not os.path.exists(file_path):
        # Return a friendly JSON error message
        return JsonResponse({
            'error': 'File not found',
            'message': 'The requested file does not exist. It may have been deleted or moved. Please re-upload the file or contact your administrator.',
            'path': path
        }, status=404)

    # Check if it's a directory
    if os.path.isdir(file_path):
        return JsonResponse({
            'error': 'Invalid request',
            'message': 'Cannot serve directories',
            'path': path
        }, status=400)

    # Serve the file
    try:
        # Guess the content type
        content_type, _ = mimetypes.guess_type(file_path)

        # Open and serve the file
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response
    except Exception as e:
        return JsonResponse({
            'error': 'Error serving file',
            'message': str(e),
            'path': path
        }, status=500)
