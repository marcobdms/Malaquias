from pypdf import PdfReader

def extract_text_from_pdf(file) -> str:
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error leyendo PDF: {e}")