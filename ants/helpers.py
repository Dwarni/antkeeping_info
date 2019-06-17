DEFAULT_NONE_STR = 'No information.'
DEFAULT_NONE_RANGE_STR = '?'


def format_value(int_value, unit_symbol, none_str=DEFAULT_NONE_STR):
    if int_value is None:
        return DEFAULT_NONE_STR
    if unit_symbol is None:
        return str(int_value)
    return '{} {}'.format(int_value, unit_symbol)


def format_min_max_integer_range(min_value, max_value, unit_symbol):
    return ('{} - {}'
            .format(
                format_value(min_value, unit_symbol),
                format_value(max_value, unit_symbol)
            ))


def format_integer_range(int_range, unit_symbol):
    if int_range is None:
        return DEFAULT_NONE_STR
    if int_range.lower == int_range.upper + 1:
        return format_value(int_range.lower, unit_symbol)
    return format_min_max_integer_range(
        int_range.lower,
        int_range.upper - 1,
        unit_symbol
    )
