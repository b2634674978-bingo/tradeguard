from tradeguard.normalize import (
    company_key,
    digits_only,
    format_phone,
    mask_phone,
    normalize_phone,
    phone_variants,
)


def test_digits_only():
    assert digits_only("+86 (138) 0013-8000") == "8613800138000"
    assert digits_only(None) == ""


def test_normalize_phone_variants():
    assert normalize_phone("+1 555 010 4477") == "15550104477"
    assert normalize_phone("0086 138 0013 8000") == "8613800138000"
    assert normalize_phone("13800138000", default_cc="86") == "8613800138000"
    assert normalize_phone("(555) 010-4477", default_cc="1") == "15550104477"


def test_normalize_phone_rejects_bad_values():
    assert normalize_phone("") is None
    assert normalize_phone("123") is None
    assert normalize_phone("0000000000") is None
    assert normalize_phone("2024-05-01") is None


def test_phone_variants_respect_explicit_prefix():
    assert phone_variants("+1 555 010 4477") == ["15550104477"]
    assert "15550104477" in phone_variants("5550104477")
    assert "8613800138000" in phone_variants("13800138000")


def test_format_and_mask():
    assert format_phone("8613800138000") == "+8613800138000"
    masked = mask_phone("8613800138000")
    assert masked.startswith("+86")
    assert masked.endswith("8000")
    assert "***" in masked


def test_company_key():
    assert company_key("NovaPeak Supplements LLC") == "novapeaksupplements"
    assert company_key("深圳市某某贸易有限公司") == "深圳市某某"
