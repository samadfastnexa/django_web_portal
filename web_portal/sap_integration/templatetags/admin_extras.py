from django import template
from web_portal.admin import admin_site
import json

register = template.Library()

@register.filter
def jsonify(value):
    """Serialize a Python object to a JSON string safe for use in HTML attributes."""
    return json.dumps(value, default=str)

@register.simple_tag(takes_context=True)
def get_all_app_list(context):
    request = context.get('request')
    if request is None:
        return []
    try:
        return admin_site.get_app_list(request)
    except Exception:
        return []

