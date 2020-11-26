"""
Additional trafaret's fields
============================
"""

import decimal
import numbers
from typing import Optional, Any

import trafaret as t
from trafaret.lib import STR_TYPES


class DecimalTrafaret(t.Float):
    convertable = STR_TYPES + (numbers.Real, int, float)
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
        super().__init__(**kwargs)

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

    def _check(self, data: Any) -> decimal.Decimal:
        value = super()._check(data)

        if self.allow_nan:
            if value.is_nan():
                return decimal.Decimal('NaN')  # avoid sNaN, -sNaN and -NaN
        else:
            if value.is_nan() or value.is_infinite():
                self._failure(
                    error='Special numeric values are not permitted.',
                    value=value,
                )

        if self.places is not None and value.is_finite():
            try:
                value = value.quantize(self.places, rounding=self.rounding)
            except decimal.InvalidOperation:
                self._failure(
                    error='Decimal can not be properly quantized.',
                    value=value,
                )

        return value

    def check_and_return(self, data: Any) -> decimal.Decimal:
        return self._check(data)
