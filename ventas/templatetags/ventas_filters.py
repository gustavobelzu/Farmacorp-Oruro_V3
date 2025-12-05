from django import template
register = template.Library()

@register.filter
def multiply_ventas(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


# Alias 'multiply' to be compatible with templates that use |multiply
@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
