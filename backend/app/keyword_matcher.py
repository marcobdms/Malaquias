# keyword_matcher.py
# Thin wrapper — la lógica real vive en matcher.py
# Este módulo existe para que el benchmark (Fase 2) pueda importarlo directamente.

from .matcher import tokenize, get_ngrams, keyword_score  # noqa: F401