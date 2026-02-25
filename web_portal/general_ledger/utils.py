"""
Utility functions for General Ledger app
"""
import os
import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger("general_ledger")


def _load_env_file(path: str) -> None:
    """Load environment variables from a .env file."""
    if not path or not os.path.isfile(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


def _ensure_env_loaded():
    """Ensure .env files are loaded into environment."""
    try:
        from django.conf import settings
        base_dir = getattr(settings, 'BASE_DIR', None)
        if base_dir:
            # Try multiple locations for .env file
            _load_env_file(os.path.join(str(base_dir), '.env'))
            _load_env_file(os.path.join(str(Path(base_dir).parent), '.env'))
        # Also try current working directory
        _load_env_file(os.path.join(os.getcwd(), '.env'))
    except Exception:
        pass


def get_hana_connection(company_db_key: Optional[str] = None):
    """
    Get HANA database connection with proper schema selection.
    
    Args:
        company_db_key: Company key like '4B-BIO' or '4B-ORANG'
    
    Returns:
        HANA database connection object
    """
    # Ensure .env file is loaded
    _ensure_env_loaded()
    
    try:
        from hdbcli import dbapi
    except ImportError:
        raise ImportError("hdbcli package not installed. Run: pip install hdbcli")
    
    # Get connection parameters from environment (no hardcoded defaults)
    host = os.environ.get('HANA_HOST', '')
    port = int(os.environ.get('HANA_PORT', '30015'))
    user = os.environ.get('HANA_USER', '')
    password = os.environ.get('HANA_PASSWORD', '')
    encrypt = os.environ.get('HANA_ENCRYPT', 'true').lower() == 'true'
    
    if not host or not user or not password:
        raise ValueError("Missing HANA connection configuration. Set HANA_HOST, HANA_USER, HANA_PASSWORD environment variables.")
    
    # Determine schema from company database key
    schema = get_schema_from_company_key(company_db_key)
    
    # Clean schema name (remove any quotes)
    schema = schema.strip().strip('"').strip("'") if schema else '4B-BIO_APP'
    
    logger.info(f"Connecting to HANA: {host}:{port} with schema: {schema}")
    
    # Create connection
    conn = dbapi.connect(
        address=host,
        port=port,
        user=user,
        password=password,
        encrypt=encrypt,
        sslValidateCertificate=False
    )
    
    # Set schema
    if schema:
        cursor = conn.cursor()
        # Use proper quoting for schema name
        cursor.execute(f'SET SCHEMA "{schema}"')
        cursor.close()
        logger.info(f"Schema set to: {schema}")
    
    return conn


def get_schema_from_company_key(company_db_key: Optional[str] = None) -> str:
    """
    Get HANA schema name from company database key.
    
    Args:
        company_db_key: Company key or schema name (e.g., '4B-BIO', '4B-BIO_APP', '4B-AGRI_LIVE')
    
    Returns:
        Schema name to use for HANA connection
    """
    # Known schema suffixes - schemas ending with these are used as-is
    SCHEMA_SUFFIXES = ('_APP', '_LIVE', '_TEST', '_DEV', '_PROD')
    
    if not company_db_key:
        # Ultimate fallback to environment variable or default
        return os.environ.get('HANA_SCHEMA', '4B-BIO_APP').strip().strip('"').strip("'")
    
    # Clean the key
    company_db_key = company_db_key.strip().strip('"').strip("'")
    
    # Normalize: Convert 4B_XXX pattern to 4B-XXX (handle URL-friendly underscore vs actual hyphen)
    # Schema names follow pattern: 4B-COMPANY_SUFFIX (hyphen after 4B, underscore before suffix)
    if company_db_key.startswith('4B_'):
        company_db_key = '4B-' + company_db_key[3:]
        logger.info(f"Normalized schema name: {company_db_key}")
    
    # If key already ends with a known suffix, use it as-is
    if any(company_db_key.endswith(suffix) for suffix in SCHEMA_SUFFIXES):
        logger.info(f"Using schema directly: {company_db_key}")
        return company_db_key
    
    # Try to get schema mapping from Django settings (SAP_COMPANY_DB)
    try:
        from preferences.models import Setting
        setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
        if setting:
            db_options = {}
            # Handle both dict (JSONField) and string (TextField) formats
            if isinstance(setting.value, dict):
                db_options = setting.value
            elif isinstance(setting.value, str):
                try:
                    import json
                    db_options = json.loads(setting.value)
                except:
                    pass
            
            # Clean up keys and values and search for match
            for k, v in db_options.items():
                clean_key = k.strip().strip('"').strip("'")
                clean_value = v.strip().strip('"').strip("'")
                if clean_key == company_db_key:
                    logger.info(f"Found schema mapping: {company_db_key} -> {clean_value}")
                    return clean_value
    except Exception as e:
        logger.warning(f"Could not fetch schema from settings: {e}")
    
    # If no mapping found, append default suffix (_APP) to the key
    default_schema = f"{company_db_key}_APP"
    logger.info(f"No mapping found, using default suffix: {default_schema}")
    return default_schema


def get_company_options() -> dict:
    """
    Get available company database options.
    
    Returns:
        Dict of company keys to schema names
    """
    try:
        from preferences.models import Setting
        setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
        if setting and isinstance(setting.value, dict):
            return setting.value
    except Exception:
        pass
    
    # Default options
    return {
        '4B-BIO': '4B-BIO_APP',
        '4B-ORANG': '4B-ORANG_APP',
    }


def format_amount(value, decimals: int = 2) -> str:
    """
    Format numeric amount with thousand separators.
    
    Args:
        value: Numeric value to format
        decimals: Number of decimal places
    
    Returns:
        Formatted string like "1,234.56"
    """
    if value is None:
        return "0.00"
    
    try:
        return f"{float(value):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def calculate_running_balance(transactions: list) -> list:
    """
    Calculate running balance for a list of transactions.
    Modifies the transactions list in-place by adding 'RunningBalance' field.
    
    Args:
        transactions: List of transaction dicts with 'Debit' and 'Credit' fields
    
    Returns:
        Modified transactions list with 'RunningBalance' added
    """
    balance = 0
    
    for txn in transactions:
        debit = float(txn.get('Debit', 0) or 0)
        credit = float(txn.get('Credit', 0) or 0)
        balance += (debit - credit)
        txn['RunningBalance'] = balance
    
    return transactions


def group_by_account(transactions: list) -> dict:
    """
    Group transactions by account code.
    
    Args:
        transactions: List of transaction dicts
    
    Returns:
        Dict with account codes as keys and transaction lists as values
    """
    grouped = {}
    
    for txn in transactions:
        account = txn.get('Account')
        if not account:
            continue
        
        if account not in grouped:
            grouped[account] = {
                'Account': account,
                'AccountName': txn.get('AccountName', ''),
                'transactions': []
            }
        
        grouped[account]['transactions'].append(txn)
    
    return grouped


def calculate_totals(transactions: list) -> dict:
    """
    Calculate total debit and credit for a list of transactions.
    
    Args:
        transactions: List of transaction dicts with 'Debit' and 'Credit' fields
    
    Returns:
        Dict with 'TotalDebit', 'TotalCredit', and 'Balance'
    """
    total_debit = sum(float(t.get('Debit', 0) or 0) for t in transactions)
    total_credit = sum(float(t.get('Credit', 0) or 0) for t in transactions)
    
    return {
        'TotalDebit': total_debit,
        'TotalCredit': total_credit,
        'Balance': total_debit - total_credit
    }
