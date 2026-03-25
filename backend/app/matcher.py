KEYWORDS_PENALTY = [
    "ventas", "sales", "comercial", "erp", "sap", "plc", "soldadura",
    "react", "python", "javascript", "sql", "salesforce", "hubspot"
]

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal") -> float:
    cv_lower = cv_text.lower()
    job_lower = job_description.lower()

    cv_words = set(cv_lower.split())
    # Para el matching básico, consideramos que palabras de más de 3 letras
    # tienen más sentido para evitar "de", "la", "el", "que", etc.
    job_words = set([w for w in job_lower.split() if len(w) > 3])

    if len(job_words) == 0:
        return 0.0

    common = job_words & cv_words

    # Al normalizar, el base score será más realista
    base_score = len(common) / len(job_words)

    # Escalamos el score para que no quede aplastado en números bajísimos
    # (por ej, 20% de coincidencia de palabras largas ya es muy bueno)
    scaled_score = min(1.0, base_score * 2.5)

    if strictness == "estricto":
        critical_missing = [k for k in KEYWORDS_PENALTY if k in job_lower and k not in cv_lower]
        penalty = len(critical_missing) * 0.12
    elif strictness == "normal":
        critical_missing = [k for k in KEYWORDS_PENALTY if k in job_lower and k not in cv_lower]
        penalty = len(critical_missing) * 0.06
    else:
        penalty = 0.0

    return round(max(0.0, min(1.0, scaled_score - penalty)), 2)