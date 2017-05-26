import trafaret as t
import decimal

from aiohttp_json_api.schema.trafarets import DecimalTrafaret


def test_decimal_repr():
    res = DecimalTrafaret()
    assert repr(res) == '<DecimalTrafaret>'
    res = DecimalTrafaret(gte=1)
    assert repr(res) == '<DecimalTrafaret(gte=1)>'
    res = DecimalTrafaret(lte=10)
    assert repr(res) == '<DecimalTrafaret(lte=10)>'
    res = DecimalTrafaret(gte=1, lte=10)
    assert repr(res) == '<DecimalTrafaret(gte=1, lte=10)>'


def test_decimal():
    res = DecimalTrafaret().check(1.0)
    assert res == decimal.Decimal(1.0)
    assert res == 1.0
    assert res == 1
    res = t.extract_error(DecimalTrafaret(), 1 + 3j)
    assert res == 'value is not Decimal'
    res = t.extract_error(DecimalTrafaret(), 'abc')
    assert res == "value can't be converted to Decimal"
    res = t.extract_error(DecimalTrafaret(), 1)
    assert res == decimal.Decimal(1)
    assert res == 1.0
    assert res == 1
    res = DecimalTrafaret(gte=2).check(3.0)
    assert res == decimal.Decimal(3.0)
    assert res == 3.0
    assert res == 3
    res = t.extract_error(DecimalTrafaret(gte=2), 1.0)
    assert res == 'value is less than 2'
    res = DecimalTrafaret(lte=10).check(5.0)
    assert res == decimal.Decimal(5.0)
    assert res == 5.0
    assert res == 5
    res = t.extract_error(DecimalTrafaret(lte=3), 5.0)
    assert res == 'value is greater than 3'
    res = DecimalTrafaret().check("5.0")
    assert res == decimal.Decimal(5.0)
    assert res == 5.0
    assert res == 5
