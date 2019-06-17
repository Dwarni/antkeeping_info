import sys
from datetime import timedelta
from functools import partial, wraps
from django.contrib.postgres.fields import ranges


def create_bounded_range_field(cls, unit_diff):
    class RangeField(cls):
        def __init__(self, *args, **kwargs):
            self.bounds = kwargs.pop('bounds', '[)')
            self.range_type = partial(self.range_type, bounds=self.bounds)
            super(RangeField, self).__init__(*args, **kwargs)

        def from_db_value(self, value, expression, connection):
            # we're checking if bounds differ from default value
            if self.bounds[0] == '(' and value.lower:
                value._lower = value.lower - unit_diff
            if self.bounds[1] == ']' and value.upper:
                value._upper = value.upper - unit_diff
            value._bounds = self.bounds
            return value

    RangeField.__name__ = cls.__name__
    return RangeField


DateRangeField = create_bounded_range_field(
    ranges.DateRangeField,
    timedelta(days=1)
)
DateTimeRangeField = create_bounded_range_field(
    ranges.DateTimeRangeField,
    timedelta(milliseconds=1)
)
BigIntegerRangeField = create_bounded_range_field(
    ranges.BigIntegerRangeField,
    1
)
FloatRangeField = create_bounded_range_field(
    ranges.FloatRangeField,
    sys.float_info.min
)
IntegerRangeField = create_bounded_range_field(
    ranges.IntegerRangeField,
    1
)
