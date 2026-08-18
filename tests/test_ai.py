from codey.ai import OllamaClient


def test_ollama_client_sends_local_chat_request(monkeypatch):
    import json

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"message": {"content": "Hello from local Ollama."}}).encode()

    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(req.data)
        return FakeResponse()

    monkeypatch.setattr("codey.ai.request.urlopen", fake_urlopen)

    client = OllamaClient()
    assert client.ask("What is Python?") == "Hello from local Ollama."
    assert captured["url"] == "http://127.0.0.1:11434/api/chat"
    assert captured["body"]["model"] == "qwen2.5-coder:3b"
    assert captured["body"]["stream"] is False
    assert captured["body"]["messages"][0]["content"] == "What is Python?"
