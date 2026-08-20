import pytest
from codey.ai import OllamaClient
def test_empty_prompt():
 with pytest.raises(ValueError):OllamaClient("http://127.0.0.1:11434","qwen2.5-coder:3b",1).ask("")
