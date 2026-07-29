"""A date that can be recorded with varying precision (exact day, month, or
just a year) — useful when the exact day isn't known, e.g. a colony found or
traded long ago with no surviving record of the exact date."""

import calendar
import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.utils.dateformat import format as format_date
from django.utils.translation import gettext as _

DAY = "DAY"
MONTH = "MONTH"
YEAR = "YEAR"
DATE_PRECISION_CHOICES = [
    (DAY, _("Exact day")),
    (MONTH, _("Month")),
    (YEAR, _("Year")),
]

MONTH_CHOICES = [("", "—")] + [(i, calendar.month_name[i]) for i in range(1, 13)]
DAY_CHOICES = [("", "—")] + [(i, i) for i in range(1, 32)]


def format_partial_date(date_value, precision):
    """Render a (date, precision) pair the way its precision implies:
    a year alone, "Month Year", or the full "Month Day, Year"."""
    if not date_value:
        return ""
    if precision == YEAR:
        return format_date(date_value, "Y")
    if precision == MONTH:
        return format_date(date_value, "F Y")
    return format_date(date_value, "N j, Y")


class PartialDateWidget(forms.MultiWidget):
    """Three sub-widgets: year (required if any part is given), optional
    month, optional day (only meaningful once a month is given)."""

    template_name = "ants/widgets/partial_date_widget.html"

    def __init__(self, attrs=None):
        widgets = [
            forms.NumberInput(
                attrs={"placeholder": _("Year"), "class": "form-control form-control-sm", "min": 1900, "max": 2100}
            ),
            forms.Select(choices=MONTH_CHOICES, attrs={"class": "form-select form-select-sm"}),
            forms.Select(choices=DAY_CHOICES, attrs={"class": "form-select form-select-sm"}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return [None, "", ""]
        date_value, precision = value
        if not date_value:
            return [None, "", ""]
        if precision == YEAR:
            return [date_value.year, "", ""]
        if precision == MONTH:
            return [date_value.year, date_value.month, ""]
        return [date_value.year, date_value.month, date_value.day]


class PartialDateField(forms.MultiValueField):
    """Combines year/month/day sub-fields into a (datetime.date, precision)
    tuple, or None if nothing was entered."""

    widget = PartialDateWidget

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        fields = (
            forms.IntegerField(required=False, min_value=1900, max_value=2100),
            forms.ChoiceField(required=False, choices=MONTH_CHOICES),
            forms.ChoiceField(required=False, choices=DAY_CHOICES),
        )
        super().__init__(fields=fields, require_all_fields=False, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return None
        year, month, day = data_list
        month = int(month) if month else None
        day = int(day) if day else None

        if not year:
            if month or day:
                raise ValidationError(_("Please also provide a year."))
            return None

        if day and not month:
            raise ValidationError(_("Please also provide a month."))

        try:
            if day:
                return (datetime.date(int(year), month, day), DAY)
            if month:
                return (datetime.date(int(year), month, 1), MONTH)
            return (datetime.date(int(year), 1, 1), YEAR)
        except ValueError:
            raise ValidationError(_("Please enter a valid date."))
