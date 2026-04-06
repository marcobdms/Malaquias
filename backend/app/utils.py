import re

def truncate_text(text: str, max_chars: int = 3000) -> str:
    return text[:max_chars] if len(text) > max_chars else text

def clean_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()

def validate_pdf_text(text: str) -> bool:
    return len(text.strip()) > 100

def is_valid_pdf(content_type: str, file_size: int, max_mb: int = 10) -> bool:
    """Valida que sea un PDF y no exceda el tamaño máximo de MB."""
    return content_type == "application/pdf" and file_size <= max_mb * 1024 * 1024