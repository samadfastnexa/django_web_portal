import http.client
import ssl
import json
import time
import random
import threading
import os
from urllib.parse import quote

from preferences.models import Setting
from django.core.exceptions import ImproperlyConfigured
from FieldAdvisoryService.models import Dealer

def _load_env_file(path: str) -> None:
    try:
        if os.path.isfile(path) and os.access(path, os.R_OK):
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    s = line.strip()
                    if s == '' or s.startswith('#') or '=' not in s:
                        continue
                    k, v = s.split('=', 1)
                    k = k.strip()
                    v = v.strip()
                    if v != '' and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                        v = v[1:-1]
                    if k != '' and not os.environ.get(k):
                        os.environ[k] = v
    except Exception:
        pass

def _normalize_mapping(obj):
    try:
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                k2 = str(k).strip()
                v2 = str(v).strip()
                if len(k2) >= 2 and ((k2[0] == '"' and k2[-1] == '"') or (k2[0] == "'" and k2[-1] == "'")):
                    k2 = k2[1:-1]
                if len(v2) >= 2 and ((v2[0] == '"' and v2[-1] == '"') or (v2[0] == "'" and v2[-1] == "'")):
                    v2 = v2[1:-1]
                cleaned[k2] = v2
            return cleaned
    except Exception:
        pass
    return obj

class SAPClient:
    """
    SAP Client - each instance manages its own session for a specific company database.
    Uses instance-level session storage to ensure database parameter works correctly.
    """

    _policies_cache = None
    _policies_cache_time = None
    _POLICIES_CACHE_TTL = 300  # Cache policies for 5 minutes
    _lock = threading.Lock()  # Class-level lock for cache thread safety

    def __init__(self, company_db_key=None):
        # Instance-level session management
        self._session_id = None
        self._session_time = None
        self._route_id = None
        try:
            try:
                _load_env_file(os.path.join(os.path.dirname(__file__), '.env'))
                _load_env_file(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))
                _load_env_file(os.path.join(os.getcwd(), '.env'))
            except Exception:
                pass
            # Priority 1: Try environment variables (for .env configuration)
            # Priority 2: Fall back to Django settings (for database configuration)
            
            # Get username
            self.username = os.environ.get('SAP_USERNAME')
            if not self.username:
                try:
                    sap_cred = Setting.objects.get(slug='sap_credential').value
                    if isinstance(sap_cred, str):
                        sap_cred = json.loads(sap_cred)
                    elif not isinstance(sap_cred, dict):
                        raise ImproperlyConfigured('sap_credential value must be a dict or JSON string')
                    self.username = str(sap_cred.get('Username') or '').strip()
                except Setting.DoesNotExist:
                    pass
            if not self.username:
                raise ImproperlyConfigured('SAP_USERNAME not found in settings or environment')
            
            # Get password
            self.password = os.environ.get('SAP_PASSWORD')
            if not self.password:
                try:
                    sap_cred = Setting.objects.get(slug='sap_credential').value
                    if isinstance(sap_cred, str):
                        sap_cred = json.loads(sap_cred)
                    elif not isinstance(sap_cred, dict):
                        raise ImproperlyConfigured('sap_credential value must be a dict or JSON string')
                    self.password = str(sap_cred.get('Passwords') or '').strip()
                except Setting.DoesNotExist:
                    pass
            if not self.password:
                raise ImproperlyConfigured('SAP_PASSWORD not found in settings or environment')
            
            # Get company database
            # Priority: 1. company_db_key parameter, 2. Database settings, 3. Environment variable
            self.company_db = None
            
            # First, try to resolve from database settings if a key is provided
            if company_db_key:
                try:
                    raw_db = Setting.objects.get(slug='SAP_COMPANY_DB').value
                    if isinstance(raw_db, str):
                        try:
                            parsed = json.loads(raw_db)
                        except Exception:
                            parsed = raw_db
                    else:
                        parsed = raw_db
                    parsed = _normalize_mapping(parsed)
                    if isinstance(parsed, dict):
                        picked = parsed.get(company_db_key)
                        if picked:
                            self.company_db = str(picked or '').strip()
                            # Debug logging
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"SAPClient initialized with company_db_key={company_db_key}, selected company_db={self.company_db}, available options={list(parsed.keys())}")
                except Setting.DoesNotExist:
                    pass
            
            # If still not found, try environment variable or default from settings
            if not self.company_db:
                self.company_db = os.environ.get('SAP_COMPANY_DB')
                
            if not self.company_db:
                try:
                    raw_db = Setting.objects.get(slug='SAP_COMPANY_DB').value
                    if isinstance(raw_db, str):
                        try:
                            parsed = json.loads(raw_db)
                        except Exception:
                            parsed = raw_db
                    else:
                        parsed = raw_db
                    parsed = _normalize_mapping(parsed)
                    if isinstance(parsed, dict):
                        # Fallback to first available or BIO
                        key = '4B-BIO'
                        picked = parsed.get(key) or parsed.get('4B-ORANG')
                        self.company_db = str(picked or '').strip()
                    else:
                        self.company_db = str(parsed or '').strip()
                except Setting.DoesNotExist:
                    pass
                    
            if not self.company_db:
                raise ImproperlyConfigured('SAP_COMPANY_DB not found in settings or environment')

            # Get SAP B1 Service Layer connection details
            self.host = (os.environ.get('SAP_B1S_HOST') or "fourbtest.vdc.services").strip()
            self.port = int((os.environ.get('SAP_B1S_PORT') or 50000))
            self.base_path = (os.environ.get('SAP_B1S_BASE_PATH') or "/b1s/v1").strip()
            
            # Check if we should use HTTP instead of HTTPS (to bypass SSL issues)
            self.use_http = os.environ.get('SAP_USE_HTTP', 'false').lower() in ('true', '1', 'yes')
            
            if not self.use_http:
                # Create SSL context with maximum compatibility for SAP B1 Service Layer
                # Use _create_unverified_context() instead of create_default_context()
                # because we need to disable certificate verification for self-signed certs
                try:
                    self.ssl_context = ssl._create_unverified_context()
                except AttributeError:
                    # Fallback for Python versions without _create_unverified_context
                    self.ssl_context = ssl.create_default_context()
                    self.ssl_context.check_hostname = False
                    self.ssl_context.verify_mode = ssl.CERT_NONE
                
                self.ssl_context.check_hostname = False
                self.ssl_context.verify_mode = ssl.CERT_NONE
                
                # Configure TLS version support (SAP may use older TLS)
                try:
                    # Try to set minimum TLS version for compatibility with legacy SAP systems
                    if hasattr(ssl, 'TLSVersion'):
                        try:
                            self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                        except:
                            # Fallback to TLSv1 if TLSv1.2 causes issues
                            try:
                                self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1
                            except:
                                pass
                    else:
                        # Fallback for older Python versions - disable TLS restrictions
                        self.ssl_context.options &= ~ssl.OP_NO_TLSv1
                        self.ssl_context.options &= ~ssl.OP_NO_TLSv1_1
                except (AttributeError, ValueError):
                    pass
                
                # Set cipher suite to support older encryption (required for some SAP systems)
                try:
                    # First try a compatible cipher suite
                    self.ssl_context.set_ciphers('ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256:AES256-GCM-SHA384:AES128-GCM-SHA256')
                except ssl.SSLError:
                    try:
                        # Fallback to broader cipher set
                        self.ssl_context.set_ciphers('DEFAULT:!aNULL:!eNULL:!MD5:!3DES:!DES:!RC4:!IDEA:!SEED:!aDSS:!SRP:!PSK')
                    except ssl.SSLError:
                        try:
                            # Last resort: use all ciphers
                            self.ssl_context.set_ciphers('ALL')
                        except ssl.SSLError:
                            # Give up on cipher configuration
                            pass
            else:
                self.ssl_context = None
            
        except Exception as e:
            raise ImproperlyConfigured(f'SAP configuration error: {e}')

    def _get_connection(self):
        if self.use_http:
            # Use HTTP without SSL
            return http.client.HTTPConnection(
                self.host, self.port,
                timeout=60
            )
        else:
            # Use HTTPS with SSL
            return http.client.HTTPSConnection(
                self.host, self.port,
                context=self.ssl_context,
                timeout=60
            )

    def _close_connection(self, conn):
        try:
            conn.close()
        except Exception:
            pass

    def _preflight_route(self):
        conn = self._get_connection()
        try:
            headers = {'Accept': 'application/json'}
            conn.request("GET", f"{self.base_path}/ServerVersion", '', headers)
            response = conn.getresponse()
            try:
                hdrs = response.getheaders()
                for k, v in hdrs:
                    if str(k).lower() == 'set-cookie':
                        parts = [x.strip() for x in str(v).split(';')]
                        for p in parts:
                            if p.startswith('ROUTEID='):
                                self._route_id = p.split('=', 1)[1]
                                break
            except Exception:
                pass
        finally:
            self._close_connection(conn)

    def _login(self):
        """Perform login and return a new session ID."""
        # Skip preflight to speed up login - SAP will handle routing automatically
        # self._preflight_route()  # Disabled for performance
        login_data = {
            'UserName': self.username,
            'Password': self.password,
            'CompanyDB': self.company_db
        }
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[SAP LOGIN] Attempting login with:")
        logger.info(f"  Host: {self.host}:{self.port}")
        logger.info(f"  Base Path: {self.base_path}")
        logger.info(f"  UserName: {self.username}")
        logger.info(f"  CompanyDB: {self.company_db}")
        logger.info(f"  Password length: {len(self.password)}")
        
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

        def do_login(data, base_path):
            conn = self._get_connection()
            try:
                req_headers = dict(headers)
                if self._route_id:
                    req_headers['Cookie'] = f"ROUTEID={self._route_id}"
                conn.request("POST", f"{base_path}/Login", json.dumps(data), req_headers)
                response = conn.getresponse()
                response_data = response.read()

                if response.status != 200:
                    error_detail = response_data.decode('utf-8')
                    logger.error(f"[SAP LOGIN] Failed with status {response.status}")
                    logger.error(f"[SAP LOGIN] Error response: {error_detail}")
                    logger.error(f"[SAP LOGIN] Attempted login: UserName={self.username}, CompanyDB={self.company_db}")
                    logger.error(f"[SAP LOGIN] Host: {self.host}:{self.port}")
                    logger.error(f"[SAP LOGIN] Base Path: {self.base_path}")
                    raise Exception(f"Login failed with status {response.status}: {error_detail}")

                login_response = json.loads(response_data.decode('utf-8'))
                try:
                    hdrs = response.getheaders()
                    for k, v in hdrs:
                        if str(k).lower() == 'set-cookie':
                            parts = [x.strip() for x in str(v).split(';')]
                            for p in parts:
                                if p.startswith('ROUTEID='):
                                    self._route_id = p.split('=', 1)[1]
                                    break
                except Exception:
                    pass
                if isinstance(login_response, dict):
                    sid = login_response.get('SessionId')
                    if sid:
                        return sid
                raise Exception('Invalid SAP login response')
            finally:
                self._close_connection(conn)

        try:
            return do_login(login_data, self.base_path)
        except ssl.SSLError as ssl_err:
            import logging
            logger = logging.getLogger(__name__)
            error_str = str(ssl_err)
            
            logger.error(f"[SAP SSL ERROR during login] {error_str}")
            
            # If it's an internal error from SAP, retry with exponential backoff
            if 'TLSV1_ALERT_INTERNAL_ERROR' in error_str or 'alert internal error' in error_str:
                max_retries = 3
                for attempt in range(1, max_retries):
                    wait_time = 2 ** (attempt - 1)  # 1s, 2s
                    logger.info(f"[SAP LOGIN] SSL error - retrying in {wait_time}s (attempt {attempt}/{max_retries})...")
                    time.sleep(wait_time)
                    try:
                        return do_login(login_data, self.base_path)
                    except ssl.SSLError:
                        if attempt == max_retries - 1:
                            # Last attempt failed
                            logger.error(f"[SAP LOGIN] Max SSL retries ({max_retries}) reached. Giving up.")
                            raise Exception(
                                f"SAP Server SSL Internal Error - The SAP B1 Service Layer at {self.host}:{self.port} is experiencing persistent SSL issues. "
                                f"Attempted {max_retries} times with exponential backoff. "
                                f"Please check if SAP B1 Service Layer is running properly or contact your SAP administrator."
                            )
                        continue
                    except Exception as other_err:
                        # Non-SSL error, propagate immediately
                        raise other_err
            raise ssl_err
        except Exception as e:
            msg = str(e)
            try:
                from preferences.models import Setting
                alt_user = None
                alt_pass = None
                alt_db = None
                try:
                    s = Setting.objects.get(slug='sap_credential').value
                    if isinstance(s, str):
                        s = json.loads(s)
                    alt_user = str(s.get('Username') or '').strip()
                    alt_pass = str(s.get('Passwords') or '').strip()
                except Exception:
                    pass
                try:
                    raw_db = Setting.objects.get(slug='SAP_COMPANY_DB').value
                    if isinstance(raw_db, str):
                        try:
                            parsed = json.loads(raw_db)
                        except Exception:
                            parsed = raw_db
                    else:
                        parsed = raw_db
                    parsed = _normalize_mapping(parsed)
                    if isinstance(parsed, dict):
                        key = '4B-ORANG'
                        picked = parsed.get(key) or parsed.get('4B-ORANG') or parsed.get('4B-BIO')
                        alt_db = str(picked or '').strip()
                    else:
                        alt_db = str(parsed or '').strip()
                except Exception:
                    pass
                data2 = {
                    'UserName': alt_user or login_data['UserName'],
                    'Password': alt_pass or login_data['Password'],
                    'CompanyDB': alt_db or login_data['CompanyDB'],
                }
                if data2['UserName'] and data2['Password'] and data2['CompanyDB']:
                    return do_login(data2, self.base_path)
            except Exception:
                pass
            raise Exception(msg)

    def get_session_id(self):
        """Return a session ID for this instance, refreshing if needed."""
        if (
            not self._session_id or
            not self._session_time or
            (time.time() - self._session_time > 300)
        ):
            self._session_id = self._login()
            self._session_time = time.time()
        return self._session_id

    def _make_request(self, method, path, body='', retry=True, attempt=0, max_ssl_retries=3):
        cookie = f"B1SESSION={self.get_session_id()}"
        if self._route_id:
            cookie = cookie + f"; ROUTEID={self._route_id}"
        headers = {'Cookie': cookie, 'Accept': 'application/json'}
        if method in ('POST', 'PUT', 'PATCH'):
            headers['Content-Type'] = 'application/json'
        
        conn = self._get_connection()
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            response_bytes = response.read()
            response_text = ''
            try:
                response_text = response_bytes.decode('utf-8')
            except Exception:
                try:
                    response_text = response_bytes.decode('latin-1')
                except Exception:
                    response_text = ''

            parsed_json = None
            try:
                parsed_json = json.loads(response_text) if response_text else None
            except Exception:
                parsed_json = None
            if 200 <= response.status < 300:
                if isinstance(parsed_json, (dict, list)):
                    return parsed_json
                # For primitive JSON (e.g., a string) or non-JSON responses, return a structured dict
                try:
                    hdrs = dict(response.getheaders())
                except Exception:
                    hdrs = {}
                return {
                    'status': response.status,
                    'headers': hdrs,
                    'body': response_text,
                }

            error_msg = ''
            error_code = ''
            if isinstance(parsed_json, dict):
                error_data = parsed_json.get('error', {})
                if isinstance(error_data, dict):
                    message_data = error_data.get('message', {})
                    if isinstance(message_data, dict):
                        error_msg = message_data.get('value', '')
                    error_code = error_data.get('code', '')

            # Retry once for cache/session/internal errors by forcing a relogin
            internal_error = response.status >= 500 or error_code in [299]
            cache_failure = 'Critical cache refresh failure' in (error_msg or response_text)
            session_invalid = (
                'Invalid session' in (error_msg or '') or
                'session already timeout' in (error_msg or '') or
                error_code in [-2001, -1101, -1001, 301]
            )
            if retry and (cache_failure or session_invalid or internal_error):
                # Invalidate this instance's session
                self._session_id = None
                self._session_time = None
                time.sleep(random.uniform(0.1, 0.3))
                return self._make_request(method, path, body, retry=False, attempt=attempt, max_ssl_retries=max_ssl_retries)

            try:
                hdrs = dict(response.getheaders())
            except Exception:
                hdrs = {}

            detail = {
                'status': response.status,
                'error_code': error_code,
                'message': error_msg or response_text,
                'body': parsed_json if parsed_json is not None else response_text,
                'headers': hdrs,
            }

            raise Exception(json.dumps(detail))
        
        except ssl.SSLError as e:
            import logging
            logger = logging.getLogger(__name__)
            error_str = str(e)
            
            # Log SSL error details
            logger.error(f"[SAP SSL ERROR - Attempt {attempt + 1}/{max_ssl_retries}] {error_str}")
            logger.error(f"[SAP SSL ERROR] Host: {self.host}:{self.port}")
            
            # If it's an internal error from SAP, retry with exponential backoff
            if 'TLSV1_ALERT_INTERNAL_ERROR' in error_str or 'alert internal error' in error_str:
                if attempt < max_ssl_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    logger.info(f"[SAP SSL ERROR] Detected SAP internal SSL error - retrying in {wait_time}s (attempt {attempt + 1}/{max_ssl_retries})...")
                    time.sleep(wait_time)
                    # Increment attempt counter and retry
                    return self._make_request(method, path, body, retry=True, attempt=attempt + 1, max_ssl_retries=max_ssl_retries)
                else:
                    # After max retries, provide helpful error message
                    logger.error(f"[SAP SSL ERROR] Max retries ({max_ssl_retries}) reached. Giving up on SSL recovery.")
                    raise Exception(
                        f"SAP Server SSL Internal Error - The SAP B1 Service Layer at {self.host}:{self.port} is experiencing persistent SSL issues. "
                        f"Attempted {max_ssl_retries} times with exponential backoff. "
                        f"Possible causes: (1) Server is overloaded or restarting, (2) SSL certificate configuration issue on SAP server, "
                        f"(3) Network connectivity problem, (4) SAP B1 Service Layer is down. "
                        f"Please check SAP server logs, restart the B1 Service Layer, or contact your SAP administrator."
                    )
            
            # Re-raise other SSL errors
            logger.error(f"[SAP SSL ERROR] Non-recoverable SSL error: {error_str}")
            raise e
        
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

    def get_projects(self, select: str = None, filter_: str = None):
        """
        Fetch SAP Projects via Service Layer.
        - select: comma-separated fields to select
        - filter_: OData filter expression
        Returns list of project dicts.
        """
        # Removed jitter for performance - SAP handles concurrent session conflicts
        query_parts = []
        if select:
            query_parts.append(f"$select={quote(select)}")
        if filter_:
            query_parts.append(f"$filter={quote(filter_)}")
        query = f"?{'&'.join(query_parts)}" if query_parts else ""
        path = f"{self.base_path}/Projects{query}"
        result = self._make_request("GET", path)
        return result.get('value', [])

    def get_all_policies(self, use_cache=True):
        """
        List all policies from Projects using UDF `U_pol`.
        Returns a list of policies with basic project context.
        
        Args:
            use_cache: If True, cache policies for 5 minutes to improve performance
        """
        # Check cache first if enabled
        if use_cache:
            with self._lock:
                if (self._policies_cache is not None and 
                    self._policies_cache_time is not None and
                    (time.time() - self._policies_cache_time < self._POLICIES_CACHE_TTL)):
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"[SAP POLICIES] Returning cached policies (age: {time.time() - self._policies_cache_time:.1f}s)")
                    return self._policies_cache
        
        # Fetch fresh from SAP
        projects = self.get_projects(select="Code,Name,ValidFrom,ValidTo,Active,U_pol")
        policies = []
        for p in projects:
            policy_val = p.get('U_pol')
            if policy_val is None:
                continue
            # Exclude empty strings
            if isinstance(policy_val, str) and not policy_val.strip():
                continue
            policies.append({
                'code': p.get('Code'),
                'name': p.get('Name'),
                'valid_from': p.get('ValidFrom'),
                'valid_to': p.get('ValidTo'),
                'active': p.get('Active'),
                'policy': policy_val
            })
        
        # Cache the result
        if use_cache:
            with self._lock:
                self._policies_cache = policies
                self._policies_cache_time = time.time()
        
        return policies

    def _logout(self):
        """Invalidate session for this instance."""
        if not self._session_id:
            return
        headers = {'Cookie': f'B1SESSION={self._session_id}'}
        conn = self._get_connection()
        try:
            conn.request("POST", f"{self.base_path}/Logout", '', headers)
            conn.getresponse().read()
        except Exception:
            pass
        finally:
            self._close_connection(conn)
            self._session_id = None
            self._session_time = None

    def get_territory_id_by_name(self, name: str):
        try:
            filt = quote(f"Name eq '{name}'")
            path = f"{self.base_path}/Territories?$filter={filt}"
            res = self._make_request("GET", path)
            if isinstance(res, dict) and 'value' in res and len(res['value']) > 0:
                row = res['value'][0]
                return (
                    row.get('territryID') or
                    row.get('TerritoryId') or
                    row.get('TerritoryID') or
                    row.get('ID') or
                    row.get('Code')
                )
        except Exception:
            pass
        return None

    def create_business_partner(self, payload: dict):
        body = json.dumps(payload)
        path = f"{self.base_path}/BusinessPartners"
        return self._make_request("POST", path, body)

    def create_sales_order(self, payload: dict):
        body = json.dumps(payload)
        path = f"{self.base_path}/Orders"
        return self._make_request("POST", path, body)

    def add_contact_employee(self, card_code: str, contact: dict):
        body = json.dumps(contact)
        cc = quote(card_code)
        path = f"{self.base_path}/BusinessPartners('{cc}')/ContactEmployees"
        return self._make_request("POST", path, body)

    def get_business_partner(self, card_code: str, expand_contacts: bool = False):
        cc = quote(card_code)
        path = f"{self.base_path}/BusinessPartners('{cc}')"
        if expand_contacts:
            path += "?$expand=ContactEmployees"
        return self._make_request("GET", path)

    def list_business_partners(self, top: int = 100, skip: int = 0, select: str = None):
        qs = []
        if select:
            qs.append(f"$select={quote(select)}")
        if top is not None:
            qs.append(f"$top={int(top)}")
        if skip:
            qs.append(f"$skip={int(skip)}")
        q = ("?" + "&".join(qs)) if qs else ""
        path = f"{self.base_path}/BusinessPartners{q}"
        res = self._make_request("GET", path)
        if isinstance(res, dict) and 'value' in res:
            return res['value']
        return res

    def post(self, resource: str, payload: dict):
        """Generic POST helper for Service Layer resources.
        Example: post('Orders', payload) -> POST /b1s/v2/Orders
        """
        if not resource or not isinstance(resource, str):
            raise ValueError("resource must be a non-empty string")
        body = json.dumps(payload or {})
        # Allow callers to pass either 'Orders' or '/Orders'
        if resource.startswith('/'):
            path = f"{self.base_path}{resource}"
        else:
            path = f"{self.base_path}/{resource}"
        return self._make_request("POST", path, body)

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
