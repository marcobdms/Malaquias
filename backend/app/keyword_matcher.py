def keyword_score(cv_text: str, job_description: str) -> float:
    cv_tokens = set(tokenize(cv_text))
    job_tokens = tokenize(job_description)
    
    if not job_tokens:
        return 0.0
    
    job_unique = set(job_tokens)
    matches = len(cv_tokens & job_unique)
    score = matches / len(job_unique)
    return min(1.0, score * 2.5)