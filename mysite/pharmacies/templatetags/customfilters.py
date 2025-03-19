from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        result = float(value) * float(arg)
        return round(result, 2)
    except (ValueError, TypeError):
        return None
