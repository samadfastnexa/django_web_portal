"""
Custom template filters for General Ledger
"""
from django import template

register = template.Library()


@register.filter(name='abs')
def abs_filter(value):
    """
    Returns the absolute value of a number.
    Usage: {{ value|abs }}
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter(name='format_amount')
def format_amount(value):
    """
    Format amount with comma separators.
    Usage: {{ value|format_amount }}
    """
    try:
        val = float(value)
        return f"{val:,.2f}"
    except (ValueError, TypeError):
        return value
