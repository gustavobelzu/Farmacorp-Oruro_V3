from django import template
from decimal import Decimal
import math

register = template.Library()

@register.filter(name='abs')
def abs_filter(value):
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value