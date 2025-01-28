from django import template

register = template.Library()

@register.filter
def make_number(value):
    """
    Converts a lowercase file letter ('a' to 'h') to a number (0 to 7).
    """
    return ord(value) - ord('a')
