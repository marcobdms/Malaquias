KEYWORDS_PENALTY = [
    "ventas", "sales", "comercial", "erp", "sap", "plc", "soldadura",
    "react", "python", "javascript", "sql", "salesforce", "hubspot"
]

def compare_cv_to_job(cv_text: str, job_description: str, strictness: str = "normal") -> float:
    cv_lower = cv_text.lower()
    job_lower = job_description.lower()

    job_words = set(job_lower.split())
    cv_words = set(cv_lower.split())

    common = job_words & cv_words
    if len(job_words) == 0:
        return 0.0

    base_score = len(common) / len(job_words)

    if strictness == "estricto":
        critical_missing = [k for k in KEYWORDS_PENALTY if k in job_lower and k not in cv_lower]
        penalty = len(critical_missing) * 0.12
    elif strictness == "normal":
        critical_missing = [k for k in KEYWORDS_PENALTY if k in job_lower and k not in cv_lower]
        penalty = len(critical_missing) * 0.06
    else:
        penalty = 0.0

    return round(max(0.0, min(1.0, base_score - penalty)), 2)