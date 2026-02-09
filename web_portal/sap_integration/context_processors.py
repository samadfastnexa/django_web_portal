"""Context processors for SAP integration."""
import json
import os


def db_selector(request):
    """Add database selector options to all admin pages."""
    db_options = {}
    selected_db_key = request.session.get('selected_db', '4B-BIO')
    
    try:
        # First, try to get options from Company model (dynamic)
        from FieldAdvisoryService.models import Company
        companies = Company.objects.filter(is_active=True).order_by('Company_name')
        
        if companies.exists():
            # Build options from Company model
            # Key: Company_name (display name), Value: name (schema)
            for company in companies:
                if company.Company_name and company.name:
                    clean_key = company.Company_name.strip().strip('"').strip("'")
                    clean_value = company.name.strip().strip('"').strip("'")
                    db_options[clean_key] = clean_value
    except Exception:
        pass
    
    # Fallback: Try to get from Settings if Company model didn't work
    if not db_options:
        try:
            from preferences.models import Setting
            db_setting = Setting.objects.filter(slug='SAP_COMPANY_DB').first()
            if db_setting:
                if isinstance(db_setting.value, dict):
                    db_options = db_setting.value
                elif isinstance(db_setting.value, str):
                    try:
                        db_options = json.loads(db_setting.value)
                    except:
                        pass
        except Exception:
            pass
    
    # Final fallback to hardcoded default options
    if not db_options:
        db_options = {
            '4B-ORANG': '4B-ORANG_APP',
            '4B-BIO': '4B-BIO_APP'
        }
    
    # Clean up keys and values
    cleaned_options = {}
    for k, v in db_options.items():
        clean_key = str(k).strip().strip('"').strip("'")
        clean_value = str(v).strip().strip('"').strip("'")
        cleaned_options[clean_key] = clean_value
    
    return {
        'db_selector_options': cleaned_options,
        'selected_db': selected_db_key,
    }
