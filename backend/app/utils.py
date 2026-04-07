import re

def truncate_text(text: str, max_chars: int = 3000) -> str:
    return text[:max_chars] if len(text) > max_chars else text

def clean_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def validate_pdf_text(text: str) -> bool:
    return len(text.strip()) > 100