import json
import os
import unittest
from unittest.mock import patch

from backend.app import llm


def valid_explanation():
    return {
        "nombre_candidato": "Ana Pérez",
        "titulo_candidato": "Ingeniera de datos",
        "fortalezas": ["Python", "SQL"],
        "carencias": ["Inglés por verificar"],
        "valoracion": "El CV contiene evidencia relevante.",
        "recomendacion": "Considerar",
        "email_candidato": None,
        "telefono_candidato": None,
    }


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self.payload = status, payload
        self.headers = headers or {}

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


class FakeProvider:
    name, model = "fake", "fake-model"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return valid_explanation()


class LLMTests(unittest.TestCase):
    def test_validation_filters_fields_and_rejects_bad_recommendation(self):
        payload = valid_explanation()
        payload["inventado"] = "fuera"
        self.assertNotIn("inventado", llm.validate_explanation(payload))
        payload["recomendacion"] = "Contratar"
        with self.assertRaises(llm.LLMError):
            llm.validate_explanation(payload)

    def test_retry_after_is_honoured(self):
        session = FakeSession([
            FakeResponse(429, headers={"Retry-After": "7"}),
            FakeResponse(200, {"ok": True}),
        ])
        sleeps = []
        client = llm._HTTPClient(session=session, sleeper=sleeps.append, max_attempts=2)
        self.assertEqual(client.post("https://test", headers={}, body={}), {"ok": True})
        self.assertEqual(sleeps, [7.0])

    def test_provider_error_does_not_leak_body(self):
        client = llm._HTTPClient(
            session=FakeSession([FakeResponse(401, {"secret": "leak"})]), max_attempts=1
        )
        with self.assertRaises(llm.LLMError) as raised:
            client.post("https://test", headers={}, body={})
        self.assertNotIn("leak", str(raised.exception))

    def test_gemini_requests_structured_json(self):
        content = json.dumps(valid_explanation())
        gemini_session = FakeSession([
            FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": content}]}}]})
        ])
        gemini = llm.GeminiProvider("key", "model", llm._HTTPClient(session=gemini_session))
        self.assertEqual(gemini.generate("prompt")["recomendacion"], "Considerar")
        config = gemini_session.calls[0][1]["json"]["generationConfig"]
        self.assertEqual(config["responseMimeType"], "application/json")
        self.assertEqual(config["responseSchema"], llm.EXPLANATION_SCHEMA)

    def test_disabled_provider_fails_open(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "none"}):
            result = llm.analyze_with_llm("cv", "oferta", match_score=0.99)
        self.assertIn("error", result)

    def test_score_is_not_sent_to_provider(self):
        provider = FakeProvider()
        with patch.object(llm, "get_provider", return_value=provider), patch.dict(
            os.environ, {"LLM_CACHE_TTL_SECONDS": "0"}
        ):
            llm.analyze_with_llm("cv", "oferta", match_score=0.01)
            llm.analyze_with_llm("cv", "oferta", match_score=0.99)
        self.assertEqual(provider.prompts[0], provider.prompts[1])

    def test_cache_is_opt_in_and_process_local(self):
        provider = FakeProvider()
        with patch.object(llm, "get_provider", return_value=provider), patch.dict(
            os.environ, {"LLM_CACHE_TTL_SECONDS": "60"}
        ):
            llm.analyze_with_llm("cv único", "oferta única")
            llm.analyze_with_llm("cv único", "oferta única")
        self.assertEqual(len(provider.prompts), 1)


if __name__ == "__main__":
    unittest.main()
