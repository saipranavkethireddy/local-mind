import pytest
from services.redaction import PIIRedactor

R = PIIRedactor.redact_text


@pytest.mark.parametrize("raw", [
    "mail me at john.doe+cv@example.co.in please",
    "a_b@sub.domain.org",
])
def test_emails_redacted(raw):
    out, n = R(raw)
    assert "@" not in out and n == 1


@pytest.mark.parametrize("raw", [
    "9876543210", "98765 43210", "98765-43210", "+91 98765 43210",
    "+91-9876543210", "(+91) 98765-43210", "919876543210",
])
def test_indian_phone_formats(raw):
    out, n = R(f"call {raw} now")
    assert "[REDACTED_PHONE]" in out and n == 1
    assert not any(ch.isdigit() for ch in out.replace("[REDACTED_PHONE]", ""))


def test_card_valid_luhn_redacted():
    out, n = R("card 4111 1111 1111 1111 expires soon")
    assert "[REDACTED_CARD]" in out and n == 1


def test_16_digit_non_card_left_alone():
    out, n = R("order id 4111 1111 1111 1112")   # fails Luhn
    assert n == 0 and "4111 1111 1111 1112" in out


@pytest.mark.parametrize("raw", ["2345 6789 0123", "2345-6789-0123", "234567890123"])
def test_aadhaar_formats(raw):
    out, n = R(f"id {raw}")
    assert n == 1 and "[REDACTED_" in out


def test_aadhaar_cannot_start_with_0_or_1():
    out, n = R("code 1234 5678 9012")
    assert n == 0


def test_pan():
    out, n = R("PAN ABCDE1234F here")
    assert "[REDACTED_PAN]" in out and n == 1


def test_plain_text_untouched():
    s = "Graduated in 2021 with CGPA 8.7 from IIT Delhi."
    assert R(s) == (s, 0)


def test_counts_add_up():
    out, n = R("a@b.com, 9876543210, ABCDE1234F")
    assert n == 3