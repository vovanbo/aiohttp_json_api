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
            self._failure('value is not {}'.format(self.value_type.__name__),
                          value=value)
        try:
            return self.value_type(value)
        except (ValueError, decimal.InvalidOperation):
            self._failure(
                "value can't be converted "
                "to {}".format(self.value_type.__name__),
                value=value
            )

    def check_and_return(self, data):
        data = super(DecimalTrafaret, self).check_and_return(data)

        if self.allow_nan:
            if data.is_nan():
                return decimal.Decimal('NaN')  # avoid sNaN, -sNaN and -NaN
        else:
            if data.is_nan() or data.is_infinite():
                self._failure('Special numeric values are not permitted.',
                              value=data)

        if self.places is not None and data.is_finite():
            try:
                data = data.quantize(self.places, rounding=self.rounding)
            except decimal.InvalidOperation:
                self._failure('Decimal can not be properly quantized.',
                              value=data)

        return data
