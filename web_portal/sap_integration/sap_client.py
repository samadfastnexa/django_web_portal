import http.client
import ssl
import json
import time
import random
import threading
from urllib.parse import quote

from preferences.models import Setting
from django.core.exceptions import ImproperlyConfigured
from FieldAdvisoryService.models import Dealer


class SAPClient:
    """
    SAP Client with global session storage across all requests.
    Ensures only one login happens per 5 minutes (or when session expires).
    """

    _global_session_id = None
    _global_session_time = None
    _lock = threading.Lock()

    def __init__(self):
        try:
            sap_cred = Setting.objects.get(slug='sap_credential').value
            if isinstance(sap_cred, str):
                sap_cred = json.loads(sap_cred)

            self.username = sap_cred['Username']
            self.password = sap_cred['Passwords']
            self.company_db = Setting.objects.get(slug='SAP_COMPANY_DB').value

            self.host = "fourbtest.vdc.services"
            self.port = 50000
            self.base_path = "/b1s/v1"

            self.ssl_context = ssl.create_default_context()
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
        except Setting.DoesNotExist as e:
            raise ImproperlyConfigured(f'Missing setting: {e}')

    def _get_connection(self):
        return http.client.HTTPSConnection(
            self.host, self.port,
            context=self.ssl_context,
            timeout=30
        )

    def _close_connection(self, conn):
        try:
            conn.close()
        except Exception:
            pass

    def _login(self):
        """Perform login and return a new session ID."""
        login_data = {
            'UserName': self.username,
            'Password': self.password,
            'CompanyDB': self.company_db
        }
        headers = {'Content-Type': 'application/json'}
        conn = self._get_connection()
        try:
            conn.request("POST", f"{self.base_path}/Login", json.dumps(login_data), headers)
            response = conn.getresponse()
            response_data = response.read()

            if response.status != 200:
                raise Exception(f"Login failed with status {response.status}: {response_data.decode('utf-8')}")

            login_response = json.loads(response_data.decode('utf-8'))
            return login_response.get('SessionId')
        finally:
            self._close_connection(conn)

    def get_session_id(self):
        """Return a global session ID, refreshing if needed."""
        with self._lock:
            if (
                not self._global_session_id or
                not self._global_session_time or
                (time.time() - self._global_session_time > 300)
            ):
                self._global_session_id = self._login()
                self._global_session_time = time.time()
        return self._global_session_id

    def _make_request(self, method, path, body='', retry=True):
        """Helper for SAP requests with retry on session/cache failure."""
        headers = {'Cookie': f'B1SESSION={self.get_session_id()}'}
        conn = self._get_connection()
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            response_data = response.read()

            try:
                result = json.loads(response_data.decode('utf-8'))
            except Exception:
                raise Exception(f"SAP response parse error: {response_data}")

            if response.status != 200:
                error_msg = result.get('error', {}).get('message', {}).get('value', '')
                error_code = result.get('error', {}).get('code', '')

                # Retry once if session/cache issue
                if retry and (
                    'Critical cache refresh failure' in error_msg or
                    error_code in [-2001, -1101, -1001]
                ):
                    with self._lock:
                        self._global_session_id = None  # force relogin
                    return self._make_request(method, path, body, retry=False)

                raise Exception(f"SAP error {response.status}: {error_msg or response_data.decode('utf-8')}")

            return result
        finally:
            self._close_connection(conn)

    def get_bp_basic(self, card_code: str):
        filter_param = quote(f"CardCode eq '{card_code}'")
        path = f"{self.base_path}/BusinessPartners?$filter={filter_param}"
        result = self._make_request("GET", path)
        if 'value' in result and len(result['value']) > 0:
            return result['value'][0]
        raise Exception(f"Business partner '{card_code}' not found")

    def get_bp_details(self, card_code: str, max_retries: int = 3):
        """Get business partner details with retry mechanism for cache failures"""
        for attempt in range(max_retries + 1):
            try:
                # Add small random delay to avoid concurrent session conflicts
                time.sleep(random.uniform(0.1, 0.3))
                filter_param = quote(f"CardCode eq '{card_code}'")
                select_param = quote("CardCode,CardName,CardType,CurrentAccountBalance")
                path = f"{self.base_path}/BusinessPartners?$filter={filter_param}&$select={select_param}"
                
                result = self._make_request("GET", path)
                if 'value' in result and len(result['value']) > 0:
                    return result['value'][0]
                else:
                    raise Exception(f"Business partner '{card_code}' not found")
                    
            except Exception as e:
                # If it's a cache refresh failure and we have retries left, continue
                if attempt < max_retries and ('Critical cache refresh failure' in str(e) or 'cache refresh failure' in str(e)):
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
                    continue
                else:
                    # Re-raise the exception if no retries left or different error
                    raise e

    def _logout(self):
        """Invalidate global session."""
        if not self._global_session_id:
            return
        headers = {'Cookie': f'B1SESSION={self._global_session_id}'}
        conn = self._get_connection()
        try:
            conn.request("POST", f"{self.base_path}/Logout", '', headers)
            conn.getresponse().read()
        except Exception:
            pass
        finally:
            self._close_connection(conn)
            self._global_session_id = None
            self._global_session_time = None

    def get_dealer_bp_info(self, dealer_id: int):
        try:
            dealer = Dealer.objects.get(id=dealer_id)
            if not dealer.card_code:
                raise ValueError(f"Dealer {dealer_id} has no card_code assigned")
            basic_info = self.get_bp_basic(dealer.card_code)
            detailed_info = self.get_bp_details(dealer.card_code)
            return {
                'dealer_id': dealer_id,
                'card_code': dealer.card_code,
                'basic_info': basic_info,
                'detailed_info': detailed_info
            }
        except Dealer.DoesNotExist:
            raise ValueError(f"Dealer with ID {dealer_id} not found")
