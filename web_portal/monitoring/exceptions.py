import logging

from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger('errors')


def logging_exception_handler(exc, context):
    """
    DRF EXCEPTION_HANDLER wrapper.

    Delegates to DRF's default handler (so API responses are unchanged), then
    logs the failure to logs/errors.log with the module, user and path so you
    can see *where* and *in which module* an error occurred. Server errors are
    logged with a traceback; client errors (4xx) at warning level.
    """
    response = drf_exception_handler(exc, context)

    try:
        request = context.get('request') if context else None
        view = context.get('view') if context else None
        view_module = getattr(view, '__module__', '') if view is not None else ''
        view_name = view.__class__.__name__ if view is not None else ''
        path = getattr(request, 'path', '') if request is not None else ''

        user = getattr(request, 'user', None)
        user_id = user.pk if (user is not None and getattr(user, 'is_authenticated', False)) else None

        status_code = getattr(response, 'status_code', None)

        if response is None or (status_code and status_code >= 500):
            # Unhandled by DRF (response is None) or a server error: include traceback.
            logger.exception(
                'Unhandled exception in %s.%s (user=%s) %s',
                view_module, view_name, user_id, path,
            )
        else:
            logger.warning(
                'API error %s in %s.%s (user=%s) %s: %s',
                status_code, view_module, view_name, user_id, path, exc,
            )
    except Exception:  # pragma: no cover - never let error logging raise
        pass

    return response
