"""
Additional trafaret's fields
============================
"""

import decimal
import numbers
from typing import Optional, Any

import trafaret as t


class DecimalTrafaret(t.Float):
    convertable = t.str_types + (numbers.Real, int)
    value_type = decimal.Decimal

    def __init__(
        self,
        places: Optional[int] = None,
        rounding: Optional[int] = None,
        allow_nan: bool = False,
        **kwargs: Any,
    ) -> None:
        self.allow_nan = allow_nan
        self.places = decimal.Decimal((0, (1,), -places)) if places is not None else None
        self.rounding = rounding
        super(DecimalTrafaret, self).__init__(**kwargs)

    def _converter(self, value: Any) -> decimal.Decimal:
        if not isinstance(value, self.convertable):
            self._failure(
                error=f'value is not {self.value_type.__name__}',
                value=value
            )
        try:
            return self.value_type(value)
        except (ValueError, decimal.InvalidOperation):
            self._failure(
                error=f"value can't be converted to {self.value_type.__name__}",
                value=value
            )

    def check_and_return(self, data: Any) -> decimal.Decimal:
        data = super().check_and_return(data)

        if self.allow_nan:
            if data.is_nan():
                return decimal.Decimal('NaN')  # avoid sNaN, -sNaN and -NaN
        else:
            if data.is_nan() or data.is_infinite():
                self._failure(
                    error='Special numeric values are not permitted.',
                    value=data,
                )

        if self.places is not None and data.is_finite():
            try:
                data = data.quantize(self.places, rounding=self.rounding)
            except decimal.InvalidOperation:
                self._failure(
                    error='Decimal can not be properly quantized.',
                    value=data,
                )

        return data
