import http.client
import ssl
import json
from preferences.models import Setting
from django.core.exceptions import ImproperlyConfigured
from FieldAdvisoryService.models import Dealer
from urllib.parse import urlparse, quote
import time
import random

class SAPClient:
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
            self._session_id = None
            self._session_time = None
            self._connection = None
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
        except:
            pass

    def _login(self):
        login_data = {
            'UserName': self.username,
            'Password': self.password,
            'CompanyDB': self.company_db
        }
        headers = {
            'Content-Type': 'application/json'
        }
        conn = self._get_connection()
        try:
            login_payload = json.dumps(login_data)
            conn.request("POST", f"{self.base_path}/Login", login_payload, headers)
            response = conn.getresponse()
            response_data = response.read()
            if response.status != 200:
                raise Exception(f"Login failed with status {response.status}: {response_data.decode('utf-8')}")
            login_response = json.loads(response_data.decode('utf-8'))
            self._session_id = login_response.get('SessionId')
            self._session_time = time.time()
            return self._session_id
        finally:
            self._close_connection(conn)

    @property
    def session_id(self):
        # Reuse session for up to 5 minutes
        if not self._session_id or not self._session_time or (time.time() - self._session_time > 300):
            self._login()
        return self._session_id

    def get_bp_basic(self, card_code: str):
        filter_param = quote(f"CardCode eq '{card_code}'")
        path = f"{self.base_path}/BusinessPartners?$filter={filter_param}"
        headers = {
            'Cookie': f'B1SESSION={self.session_id}'
        }
        conn = self._get_connection()
        try:
            conn.request("GET", path, '', headers)
            response = conn.getresponse()
            response_data = response.read()
            if response.status != 200:
                raise Exception(f"Get BP basic failed with status {response.status}: {response_data.decode('utf-8')}")
            result = json.loads(response_data.decode('utf-8'))
            if 'value' in result and len(result['value']) > 0:
                return result['value'][0]
            else:
                raise Exception(f"Business partner '{card_code}' not found")
        finally:
            self._close_connection(conn)

    def get_bp_details(self, card_code: str):
        # Add small random delay to avoid concurrent session conflicts
        time.sleep(random.uniform(0.1, 0.3))
        filter_param = quote(f"CardCode eq '{card_code}'")
        select_param = quote("CardCode,CardName,CardType,CurrentAccountBalance")
        path = f"{self.base_path}/BusinessPartners?$filter={filter_param}&$select={select_param}"
        headers = {
            'Cookie': f'B1SESSION={self.session_id}'
        }
        conn = self._get_connection()
        try:
            conn.request("GET", path, '', headers)
            response = conn.getresponse()
            response_data = response.read()
            # Parse response and handle SAP error codes/messages
            try:
                result = json.loads(response_data.decode('utf-8'))
            except Exception:
                raise Exception(f"Get BP details failed with status {response.status}: {response_data}")
            if response.status != 200:
                # Check for SAP error structure
                if 'error' in result and 'message' in result['error']:
                    error_msg = result['error']['message'].get('value', '')
                    error_code = result['error'].get('code', '')
                    if 'Critical cache refresh failure' in error_msg or error_code in [-2001, -1101]:
                        raise Exception(f"SAP cache refresh failure: {error_msg}")
                    else:
                        raise Exception(f"Get BP details failed with status {response.status}: {error_msg}")
                else:
                    raise Exception(f"Get BP details failed with status {response.status}: {response_data.decode('utf-8')}")
            if 'value' in result and len(result['value']) > 0:
                return result['value'][0]
            else:
                raise Exception(f"Business partner '{card_code}' not found")
        finally:
            self._close_connection(conn)

    def _logout(self):
        if not self._session_id:
            return
        headers = {
            'Cookie': f'B1SESSION={self._session_id}'
        }
        conn = self._get_connection()
        try:
            conn.request("POST", f"{self.base_path}/Logout", '', headers)
            response = conn.getresponse()
            response.read()
        except:
            pass
        finally:
            self._close_connection(conn)
            self._session_id = None
            self._session_time = None

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