import ipaddress
import logging
import time

from django.http import HttpResponseNotFound

logger = logging.getLogger('access')
security_logger = logging.getLogger('security')

# Requests whose path starts with one of these are never recorded (static assets, etc.).
SKIP_PREFIXES = ('/static/', '/media/', '/favicon.ico', '/swagger')

# Path fragments / extensions that only automated scanners request. None of
# these collide with real routes (/api, /admin, /media, /static, /swagger).
_PROBE_SUBSTRINGS = (
    '/.env', '/.git', '/.aws', '/.ssh', '/.htaccess', '/.ds_store',
    '/.vscode', '/.idea', 'wp-login', 'wp-admin', 'wp-content', 'wp-includes',
    'phpmyadmin', '/pma/', '/vendor/', 'settings.py', 'manage.py', 'wsgi.py',
    '/config.json', '/credentials',
)
_PROBE_SUFFIXES = (
    '.php', '.env', '.sql', '.bak', '.old', '.pem', '.key', '.ini',
    '.sqlite', '.sqlite3', '.asp', '.aspx', '.jsp', '.cgi',
)


def _is_probe(path):
    p = path.lower()
    return any(s in p for s in _PROBE_SUBSTRINGS) or p.endswith(_PROBE_SUFFIXES)


_AUTH_PATH_HINTS = ('/login', '/forgot-password', '/token')
_IDENTIFIER_KEYS = ('email', 'phone_number', 'phone', 'username')


def _is_auth_path(path):
    p = path.lower()
    return any(h in p for h in _AUTH_PATH_HINTS)


def _login_identifier(request):
    """Best-effort: the email/phone/username submitted to an auth endpoint.

    Reads only identifier fields -- never the password.
    """
    for key in _IDENTIFIER_KEYS:
        val = request.POST.get(key)
        if val:
            return str(val)[:254]
    try:
        import json
        data = json.loads(request.body or b'{}')
        if isinstance(data, dict):
            for key in _IDENTIFIER_KEYS:
                if data.get(key):
                    return str(data[key])[:254]
    except Exception:
        pass
    return ''

# DB rows are only written for these path prefixes (plus any response with status >= 400).
DB_RECORD_PREFIXES = ('/api/', '/admin/')


def _client_ip(request):
    """
    Best-effort real client IP.

    Behind a reverse proxy (nginx/load balancer) REMOTE_ADDR is the proxy
    itself -- typically 127.0.0.1 -- and the real caller sits in
    X-Forwarded-For (left-most entry) or X-Real-IP. We walk every candidate
    and return the first public address; if they are all private/loopback
    (normal for local development) we keep the first valid one so the column
    is never blank.
    """
    candidates = []
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    candidates.extend(part.strip() for part in xff.split(',') if part.strip())

    real_ip = (request.META.get('HTTP_X_REAL_IP') or '').strip()
    if real_ip:
        candidates.append(real_ip)

    remote = (request.META.get('REMOTE_ADDR') or '').strip()
    if remote:
        candidates.append(remote)

    first_valid = None
    for candidate in candidates:
        # Strip an IPv6 zone id / surrounding brackets some proxies emit.
        cleaned = candidate.strip('[]').split('%')[0]
        try:
            parsed = ipaddress.ip_address(cleaned)
        except ValueError:
            continue
        if first_valid is None:
            first_valid = cleaned
        if not (parsed.is_private or parsed.is_loopback or parsed.is_link_local):
            return cleaned
    return first_valid


def _classify_bad_token(raw):
    """Distinguish an expired token from a structurally invalid one (parse-only)."""
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(raw, options={'verify_signature': False})
    except Exception:
        return 'token_invalid'
    exp = payload.get('exp')
    if exp and exp < time.time():
        return 'token_expired'
    return 'token_invalid'


def _resolve_user(request):
    """
    Return (user_obj_or_None, user_id_or_None, username_str, auth_outcome).

    auth_outcome explains an unauthenticated request: '' when a valid identity
    was found, else 'no_credentials' / 'token_expired' / 'token_invalid'.

    Session/admin requests have request.user populated by AuthenticationMiddleware.
    JWT/API requests do NOT -- DRF authenticates inside the view, not in middleware --
    so we decode the Bearer access token ourselves to attribute the request.
    """
    user = getattr(request, 'user', None)
    if user is not None and getattr(user, 'is_authenticated', False):
        return user, user.pk, user.get_username(), ''

    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Bearer '):
        raw = auth.split(' ', 1)[1]
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(raw)  # verifies signature + expiry
            return None, token.get('user_id'), '', ''
        except Exception:
            return None, None, '', _classify_bad_token(raw)
    return None, None, '', 'no_credentials'


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
        # Capture the login identifier BEFORE the view reads (and consumes) the
        # request body. Reading request.body here caches it, so DRF can still parse.
        if _is_auth_path(request.path):
            try:
                request._login_identifier = _login_identifier(request)
            except Exception:
                request._login_identifier = ''
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
        _user, user_id, username, auth_outcome = _resolve_user(request)
        view_module = _view_module(request)
        who = username or (f'id={user_id}' if user_id else 'anonymous')
        # Only meaningful on auth failures; blank otherwise.
        outcome = auth_outcome if status_code in (401, 403) else ''
        # On a failed login, capture which account was targeted (never the password).
        # Read in the request phase (see __call__) so the body isn't already consumed.
        attempted = (getattr(request, '_login_identifier', '')
                     if status_code in (400, 401) else '')

        logger.info(
            'user=%s %s %s %s %sms%s',
            who, request.method, path, status_code, duration_ms,
            f' [{outcome}]' if outcome else '',
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
                auth_outcome=outcome,
                attempted_identifier=attempted,
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
                    auth_outcome=outcome,
                    attempted_identifier=attempted,
                )
            except Exception:
                pass


class SecurityProbeMiddleware:
    """
    Blocks and logs requests for paths only automated vulnerability scanners
    ask for (.env, .git, wp-admin, *.php, settings.py, ...). Returns a bare 404
    so nothing is confirmed to the scanner, and records the hit to
    logs/security.log. Placed early in MIDDLEWARE so probes never reach the
    session/CSRF/URL layer (no session write, minimal work).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if _is_probe(request.path):
            ip = _client_ip(request)
            security_logger.warning(
                'blocked probe: %s %s from %s ua=%r',
                request.method, request.path, ip,
                request.META.get('HTTP_USER_AGENT', '')[:200],
            )
            # Record it in the activity log too, flagged suspicious, so blocked
            # probes are visible in the admin (this middleware short-circuits
            # before RequestActivityMiddleware would otherwise see them).
            try:
                from .models import ActivityLog
                ActivityLog.objects.create(
                    method=request.method[:10],
                    path=request.path[:512],
                    view_module='monitoring.security',
                    status_code=404,
                    ip_address=ip,
                    is_error=True,
                    is_suspicious=True,
                )
            except Exception:
                pass
            return HttpResponseNotFound('Not found')
        return self.get_response(request)
