"""
Additional trafaret's fields
============================
"""

import decimal
import numbers

import trafaret as t


class DecimalTrafaret(t.Float):
    convertable = t.str_types + (numbers.Real, int)
    value_type = decimal.Decimal

    def __init__(self, places=None, rounding=None, allow_nan=False, **kwargs):
        self.allow_nan = allow_nan
        self.places = decimal.Decimal((0, (1,), -places)) \
            if places is not None else None
        self.rounding = rounding
        super(DecimalTrafaret, self).__init__(**kwargs)

    def _converter(self, value):
        if not isinstance(value, self.convertable):
            self._failure(f'value is not {self.value_type.__name__}',
                          value=value)
        try:
            return self.value_type(value)
        except (ValueError, decimal.InvalidOperation):
            self._failure(
                f"value can't be converted to {self.value_type.__name__}",
                value=value
            )

    def check_and_return(self, val):
        val = super(DecimalTrafaret, self).check_and_return(val)

        if self.allow_nan:
            if val.is_nan():
                return decimal.Decimal('NaN')  # avoid sNaN, -sNaN and -NaN
        else:
            if val.is_nan() or val.is_infinite():
                self._failure('Special numeric values are not permitted.',
                              value=val)

        if self.places is not None and val.is_finite():
            try:
                val = val.quantize(self.places, rounding=self.rounding)
            except decimal.InvalidOperation as exc:
                self._failure('Decimal can not be properly quantized.',
                              value=val)

        return val
