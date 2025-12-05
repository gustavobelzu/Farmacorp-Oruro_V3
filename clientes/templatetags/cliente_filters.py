from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='divide')
def divide(value, arg):
    """
    Divide el valor por el argumento.
    Uso: {{ value|divide:100 }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0