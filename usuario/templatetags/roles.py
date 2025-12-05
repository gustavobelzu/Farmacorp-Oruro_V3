from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def has_role(context, *roles):
    """Return True if current user has any of the given roles.

    Usage in template:
      {% load roles %}
      {% if has_role 'administrador' 'encargado_almacen' %} ... {% endif %}
    Superusers and staff return True for any role check.
    """
    request = context.get('request')
    if not request:
        return False
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    user_role = getattr(user, 'rol', None)
    return user_role in roles
