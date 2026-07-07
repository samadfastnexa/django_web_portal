import logging
import time

logger = logging.getLogger('access')

# Requests whose path starts with one of these are never recorded (static assets, etc.).
SKIP_PREFIXES = ('/static/', '/media/', '/favicon.ico', '/swagger')

# DB rows are only written for these path prefixes (plus any response with status >= 400).
DB_RECORD_PREFIXES = ('/api/', '/admin/')


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _resolve_user(request):
    """
    Return (user_obj_or_None, user_id_or_None, username_str).

    Session/admin requests have request.user populated by AuthenticationMiddleware.
    JWT/API requests do NOT -- DRF authenticates inside the view, not in middleware --
    so we decode the Bearer access token ourselves to attribute the request.
    """
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return user, user.pk, user.get_username()

    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Bearer '):
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(auth.split(' ', 1)[1])
            return None, token.get('user_id'), ''
        except Exception:
            return None, None, ''
    return None, None, ''


def _view_module(request):
    rm = getattr(request, 'resolver_match', None)
    if not rm or not getattr(rm, 'func', None):
        return ''
    func = rm.func
    view_class = getattr(func, 'view_class', None) or getattr(func, 'cls', None)
    if view_class is not None:
        return getattr(view_class, '__module__', '') or ''
    return getattr(func, '__module__', '') or ''


class RequestActivityMiddleware:
    """
    Logs one line per request to logs/access.log and, for API/admin actions and
    any error response, inserts a monitoring.ActivityLog row.

    All instrumentation is wrapped in try/except: logging must never break a request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = int((time.monotonic() - start) * 1000)
        try:
            self._record(request, response, duration_ms)
        except Exception:  # pragma: no cover - never let logging break the response
            pass
        return response

    def _record(self, request, response, duration_ms):
        path = request.path
        if path.startswith(SKIP_PREFIXES) or 'jsi18n' in path:
            return

        status_code = getattr(response, 'status_code', 0)
        _user, user_id, username = _resolve_user(request)
        view_module = _view_module(request)
        who = username or (f'id={user_id}' if user_id else 'anonymous')

        logger.info(
            'user=%s %s %s %s %sms',
            who, request.method, path, status_code, duration_ms,
        )

        is_error = status_code >= 400
        if not (path.startswith(DB_RECORD_PREFIXES) or is_error):
            return

        try:
            from .models import ActivityLog
            ActivityLog.objects.create(
                user_id=user_id or None,
                username=username[:150],
                method=request.method[:10],
                path=path[:512],
                view_module=view_module[:255],
                status_code=status_code,
                duration_ms=duration_ms,
                ip_address=_client_ip(request),
                is_error=is_error,
            )
        except Exception:
            # A decoded JWT user_id may not exist as a row, or the DB may be
            # unavailable -- retry once without the FK so we still capture the event.
            try:
                from .models import ActivityLog
                ActivityLog.objects.create(
                    username=username[:150],
                    method=request.method[:10],
                    path=path[:512],
                    view_module=view_module[:255],
                    status_code=status_code,
                    duration_ms=duration_ms,
                    ip_address=_client_ip(request),
                    is_error=is_error,
                )
            except Exception:
                pass
