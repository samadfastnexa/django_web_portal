from django import template
from django.contrib.admin.sites import site

register = template.Library()

@register.simple_tag(takes_context=True)
def get_all_app_list(context):
    request = context.get('request')
    if request is None:
        return []
    try:
        return site.get_app_list(request)
    except Exception:
        return []

