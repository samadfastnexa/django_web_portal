"""Context processors for SAP integration."""
import json
import os


def db_selector(request):
    """Add database selector options to all admin pages."""
    db_options = {}
    selected_db_key = request.session.get('selected_db', '4B-BIO')
    
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
    
    # Fallback to default options
    if not db_options:
        db_options = {
            '4B-ORANG': '4B-ORANG_APP',
            '4B-BIO': '4B-BIO_APP'
        }
    
    # Clean up keys and values
    cleaned_options = {}
    for k, v in db_options.items():
        clean_key = k.strip().strip('"').strip("'")
        clean_value = v.strip().strip('"').strip("'")
        cleaned_options[clean_key] = clean_value
    
    return {
        'db_selector_options': cleaned_options,
        'selected_db': selected_db_key,
    }
