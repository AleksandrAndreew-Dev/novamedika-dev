# pharmacies/templatetags/humanize_updated.py
from django import template
from datetime import date, timedelta

register = template.Library()

@register.filter
def human_updated(value):
    if not value:
        return ""
    today = date.today()
    value_date = value.date()

    if value_date == today:
        return value.strftime("%H:%M")
    elif value_date == today - timedelta(days=1):
        return "вчера"
    elif value_date == today - timedelta(days=2):
        return "два дня назад"
    else:
        return value.strftime("%d.%m.%Y %H:%M")
