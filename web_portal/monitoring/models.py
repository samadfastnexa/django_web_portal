from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    """
    One row per notable HTTP request. Written by RequestActivityMiddleware.

    This is the DB-backed usage/audit trail ("who did what, when") that mirrors
    logs/access.log. It intentionally stores only request metadata -- never
    request bodies, headers, tokens, passwords or OTPs.
    """

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # Keep the row even if the user is later deleted; username is denormalized.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='activity_logs',
    )
    username = models.CharField(max_length=150, blank=True, default='')
    method = models.CharField(max_length=10, blank=True, default='')
    path = models.CharField(max_length=512, blank=True, default='')  # path only, no query string
    view_module = models.CharField(max_length=255, blank=True, default='')
    status_code = models.PositiveIntegerField(default=0, db_index=True)
    duration_ms = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_error = models.BooleanField(default=False, db_index=True)
    # Why a 401/403 happened: '' (n/a), no_credentials, token_expired, token_invalid.
    auth_outcome = models.CharField(max_length=32, blank=True, default='', db_index=True)
    # On a failed login: the email/phone/username that was tried (never the password).
    attempted_identifier = models.CharField(max_length=254, blank=True, default='')
    # True for blocked scanner probes (.env, wp-admin, *.php, ...).
    is_suspicious = models.BooleanField(default=False, db_index=True)
    # Redacted request query string (e.g. ?database=4B-BIO_APP) -- sensitive keys masked.
    query_string = models.CharField(max_length=512, blank=True, default='')
    # For 4xx/5xx: the error message pulled from the response body (so it's visible in admin).
    error_detail = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['status_code', 'timestamp']),
        ]

    def __str__(self):
        who = self.username or 'anonymous'
        return f'{self.timestamp:%Y-%m-%d %H:%M:%S} {who} {self.method} {self.path} -> {self.status_code}'
