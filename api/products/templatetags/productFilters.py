from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter(name='divide')
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='subtract')
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='abs')
def absolute(value):
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0
    
@register.filter(name='index')
def index(lst, i):
    try:
        return lst[i]
    except:
        return None


@register.filter(name='get_id')
def get_id(obj):
    """Custom filter to access the _id attribute."""
    return getattr(obj, "_id", None)

@register.filter(name='index')
def index(lst, i):
    try:
        return lst[i]
    except:
        return None
