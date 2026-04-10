from pypdf import PdfReader
from docx import Document
import io

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

def extract_text_from_docx(file) -> str:
    try:
        content = file.read()
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs).strip()
    except Exception as e:
        raise ValueError(f"Error leyendo DOCX: {e}")

def extract_text_from_cv(filename: str, file) -> str:
    """Dispatcher: extrae texto de PDF o DOCX según la extensión del archivo."""
    name = filename.lower()
    if name.endswith(".pdf"):
        return extract_text_from_pdf(file)
    elif name.endswith(".docx"):
        return extract_text_from_docx(file)
    else:
        raise ValueError(f"Formato no soportado: {filename}. Solo se aceptan PDF y DOCX.")