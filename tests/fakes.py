from types import SimpleNamespace


class FakeClient:
    """Stands in for anthropic.Anthropic; records calls to messages.create."""

    def __init__(self, text="", error=None, blocks=None, stop_reason="end_turn"):
        if blocks is None:
            blocks = [SimpleNamespace(type="text", text=text)]
        self.blocks = blocks
        self.stop_reason = stop_reason
        self.error = error
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.blocks, stop_reason=self.stop_reason)
