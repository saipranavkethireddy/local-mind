import re

def _luhn_ok(digits: str) -> bool:
    """Luhn checksum: separates real card numbers from random long digit runs."""
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


# Order matters: cards first so long numbers are not split by the shorter patterns.
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Indian mobile: optional +91 / 91 / (+91), 10 digits starting 6-9, optional space/dash in the middle.
PHONE = re.compile(r"(?<!\d)(?:\(?\+?91\)?[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)")
# Aadhaar: 12 digits, first digit 2-9, optional single space/dash between groups of 4.
AADHAAR = re.compile(r"(?<!\d)(?<!\d[ -])[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}(?!\d)(?![ -]\d)")
# PAN: 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F).
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")


class PIIRedactor:
    @staticmethod
    def redact_text(text: str) -> tuple[str, int]:
        total = 0

        def apply(pattern, label, check=None):
            nonlocal text, total

            def repl(m):
                nonlocal total
                if check is not None and not check(re.sub(r"\D", "", m.group())):
                    return m.group()
                total += 1
                return f"[REDACTED_{label}]"

            text = pattern.sub(repl, text)

        apply(CARD, "CARD", _luhn_ok)
        apply(PHONE, "PHONE")
        apply(AADHAAR, "ID")
        apply(PAN, "PAN")
        apply(EMAIL, "EMAIL")
        return text, total