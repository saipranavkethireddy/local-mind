import re

class PIIRedactor:
    @staticmethod
    def redact_text(text: str) -> tuple[str, int]:
        redactions_count = 0
        
        # 1. Email addresses
        text, count = re.subn(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', text)
        redactions_count += count
        
        # 2. Phone numbers (Indian/International formats)
        text, count = re.subn(r'\b(?:\+?91[\-\s]?)?[6-9]\d{9}\b', '[REDACTED_PHONE]', text)
        redactions_count += count
        
        # 3. Credit Card / Long digit sequences (16 digits)
        text, count = re.subn(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', '[REDACTED_CARD]', text)
        redactions_count += count
        
        # 4. Aadhaar-like 12-digit ID numbers
        text, count = re.subn(r'\b\d{4}\s\d{4}\s\d{4}\b', '[REDACTED_ID]', text)
        redactions_count += count
        
        return text, redactions_count