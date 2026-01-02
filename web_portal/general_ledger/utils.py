"""
Utility functions for General Ledger app
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("general_ledger")


def get_hana_connection(company_db_key: Optional[str] = None):
    """
    Get HANA database connection with proper schema selection.
    
    Args:
        company_db_key: Company key like '4B-BIO' or '4B-ORANG'
    
    Returns:
        HANA database connection object
    """
    try:
        from hdbcli import dbapi
    except ImportError:
        raise ImportError("hdbcli package not installed. Run: pip install hdbcli")
    
    # Get connection parameters from environment
    host = os.environ.get('HANA_HOST', 'fourbtest.vdc.services')
    port = int(os.environ.get('HANA_PORT', '30015'))
    user = os.environ.get('HANA_USER', 'FASTAPP')
    password = os.environ.get('HANA_PASSWORD', '@uF!56%3##')
    encrypt = os.environ.get('HANA_ENCRYPT', 'true').lower() == 'true'
    
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
        company_db_key: Company key like '4B-BIO' or '4B-ORANG'
    
    Returns:
        Schema name like '4B-BIO_APP' or '4B-ORANG_APP'
    """
    # Default mapping
    schema_mapping = {
        '4B-BIO': '4B-BIO_APP',
        '4B-ORANG': '4B-ORANG_APP',
    }
    
    # Try to get from Django settings first
    if company_db_key:
        # Clean the key
        company_db_key = company_db_key.strip().strip('"').strip("'")
        
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
                
                # Clean up keys and values
                cleaned_options = {}
                for k, v in db_options.items():
                    clean_key = k.strip().strip('"').strip("'")
                    clean_value = v.strip().strip('"').strip("'")
                    cleaned_options[clean_key] = clean_value
                
                # Return cleaned value if found
                if company_db_key in cleaned_options:
                    return cleaned_options[company_db_key]
        except Exception as e:
            logger.warning(f"Could not fetch schema from settings: {e}")
    
    # Fallback to default mapping
    if company_db_key:
        company_db_key_clean = company_db_key.strip().strip('"').strip("'")
        return schema_mapping.get(company_db_key_clean, '4B-BIO_APP')
    
    # Ultimate fallback
    return os.environ.get('HANA_SCHEMA', '4B-BIO_APP').strip().strip('"').strip("'")


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
