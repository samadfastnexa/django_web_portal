import json, requests
from datetime import timedelta
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from preferences.models import Setting  # your Settings table

class SAPClient:
    def __init__(self):
        try:
            cred = Setting.objects.get(slug='sap_credential').value  # dict – no json.loads
            self.username = cred['Username']
            self.password = cred['Passwords']

            base = Setting.objects.get(slug='SAP_BASE_URL').value.rstrip('/')
            login_path = Setting.objects.get(slug='SAP_LOGIN_PATH').value
            bp_path = Setting.objects.get(slug='SAP_BP_PATH').value

            self.base_url = base
            self.login_url = base + login_path
            self.bp_url = base + bp_path
        except Setting.DoesNotExist as e:
            raise ImproperlyConfigured(f'Missing setting: {e}')

    # ---------- session ----------
    def _login(self):
        resp = requests.post(
            self.login_url,
            json={'UserName': self.username, 'Password': self.password},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        cache.set('sap_session_id', data['SessionId'], 29 * 60)  # 29 min < 30
        return data['SessionId']

    @property
    def session_id(self):
        return cache.get('sap_session_id') or self._login()

    # ---------- business partner ----------
    def get_bp(self, card_code: str):
        url = f"{self.bp_url}('{card_code}')"
        headers = {'Cookie': f'B1SESSION={self.session_id}'}
        resp = requests.get(url, headers=headers, timeout=10)

        if resp.status_code == 401:  # session expired
            headers['Cookie'] = f'B1SESSION={self._login()}'
            resp = requests.get(url, headers=headers, timeout=10)

        resp.raise_for_status()
        return resp.json()