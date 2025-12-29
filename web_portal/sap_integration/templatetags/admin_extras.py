from django import template
from web_portal.admin import admin_site

register = template.Library()

@register.simple_tag(takes_context=True)
def get_all_app_list(context):
    request = context.get('request')
    if request is None:
        return []
    try:
        return admin_site.get_app_list(request)
    except Exception:
        return []

