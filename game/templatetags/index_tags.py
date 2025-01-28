# game/templatetags/index_tags.py

from django import template

register = template.Library()

@register.filter
def index(sequence, position):
    """
    Returns the item at the given position in the sequence.
    Usage: {{ sequence|index:2 }}
    """
    try:
        return sequence[position]
    except (IndexError, TypeError):
        return ''
