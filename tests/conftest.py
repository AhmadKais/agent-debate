import pytest


@pytest.fixture(autouse=True)
def set_dummy_api_key(monkeypatch):
    """Inject a dummy API key so BaseAgent.__init__ doesn't raise during tests."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-dummy-key-for-unit-tests")
