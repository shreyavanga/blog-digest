from types import SimpleNamespace


class FakeClient:
    """Stands in for anthropic.Anthropic; records calls to messages.create."""

    def __init__(self, text="", error=None):
        self.text = text
        self.error = error
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(content=[SimpleNamespace(text=self.text)])
