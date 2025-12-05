from django import template
register = template.Library()

@register.filter
def multiply_ventas(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''

