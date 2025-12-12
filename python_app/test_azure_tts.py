import pytest

from .azure_tts import AzureTTSClient


@pytest.mark.parametrize(
    "value,default,expected",
    [
        (None, "+0%", "+0%"),
        ("", "+0%", "+0%"),
        ("+5%", "+0%", "+5%"),
        ("-3%", "+0%", "-3%"),
        ("10", "+0%", "+10%"),
        ("-1.5", "+0%", "-1.5%"),
        ("0", "+2%", "+0%"),
    ],
)
def test_normalize_prosody_valid_numbers(value, default, expected):
    assert AzureTTSClient._normalize_prosody(value, default) == expected


def test_normalize_prosody_invalid_falls_back_default(caplog):
    caplog.set_level("WARNING")
    result = AzureTTSClient._normalize_prosody("fast", "+1%")
    assert result == "+1%"
    assert "Invalid prosody value" in caplog.text
