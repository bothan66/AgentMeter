import io
import json
import urllib.error

from agentmeter.providers import probe as probe_responses


def test_probe_sends_bearer_and_preserves_full_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1/")
    monkeypatch.setenv("AGENTMETER_MODEL", "ZHIPU/GLM-5.3-Flash")

    def fake_open(request, timeout):
        assert request.full_url == "https://example.invalid/v1/responses"
        assert request.get_header("Authorization") == "Bearer test-credential"
        payload = json.loads(request.data)
        assert payload["model"] == "ZHIPU/GLM-5.3-Flash"
        assert payload["input"][0]["content"][0]["type"] == "input_text"
        response = io.StringIO(
            json.dumps(
                {
                    "status": "completed",
                    "output": [
                        {"type": "message", "content": [{"type": "output_text", "text": "OK"}]}
                    ],
                }
            )
        )
        response.status = 200
        return response

    monkeypatch.setattr(probe_responses.urllib.request, "urlopen", fake_open)
    assert probe_responses.main([]) == 0


def test_probe_reports_http_error_without_body_or_key(monkeypatch, capsys):
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AGENTMETER_MODEL", "glm5.3-flash")

    def fake_open(*args, **kwargs):
        raise urllib.error.HTTPError("https://example.invalid", 401, "test-credential", {}, None)

    monkeypatch.setattr(probe_responses.urllib.request, "urlopen", fake_open)
    assert probe_responses.main([]) == 1
    output = capsys.readouterr()
    assert "401" in output.err
    assert "test-credential" not in output.err + output.out
