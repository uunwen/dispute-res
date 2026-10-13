from types import SimpleNamespace

from app.agents.base import AgentContext
from app.agents.rider_advocate import RiderAdvocate
from app.llm.client import ChatResult, LLMClient, ToolCall
from app.schemas.evidence import EvidenceItem


def test_parse_chat_result_keeps_extra_content():
    client = LLMClient(api_key="k", mock=False)
    data = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "fake_tool", "arguments": '{"x": 1}'},
                            "thought_signature": "sig123",
                        }
                    ],
                }
            }
        ]
    }
    result = client._parse_chat_result(data)
    assert result.tool_calls[0].id == "c1"
    assert result.tool_calls[0].name == "fake_tool"
    assert result.tool_calls[0].arguments == {"x": 1}
    assert result.tool_calls[0].extra_content == {"thought_signature": "sig123"}


def test_assistant_message_no_extra_identical():
    agent = RiderAdvocate()
    result = ChatResult(
        content=None, tool_calls=[ToolCall(id="c1", name="fake_tool", arguments={"x": 1})]
    )
    msg = agent._assistant_message(result)
    assert msg["tool_calls"] == [
        {"id": "c1", "type": "function", "function": {"name": "fake_tool", "arguments": '{"x": 1}'}}
    ]


def test_assistant_message_echoes_extra():
    agent = RiderAdvocate()
    result = ChatResult(
        content=None,
        tool_calls=[
            ToolCall(id="c1", name="fake_tool", arguments={"x": 1}, extra_content={"thought_signature": "sig123"})
        ],
    )
    msg = agent._assistant_message(result)
    assert msg["tool_calls"][0]["thought_signature"] == "sig123"
    assert msg["tool_calls"][0]["id"] == "c1"
    assert msg["tool_calls"][0]["function"]["arguments"] == '{"x": 1}'


async def test_tool_call_roundtrip_with_extra_content(monkeypatch):
    class FakeChat:
        def __init__(self):
            self.calls = 0

        async def chat(self, messages, *, tools=None, tool_choice="auto", temperature=None, role="tools"):
            self.calls += 1
            if self.calls == 1:
                return ChatResult(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="c1",
                            name="fake_tool",
                            arguments={"trip_id": 1},
                            extra_content={"thought_signature": "sig123"},
                        )
                    ],
                )
            assistant = next(
                (m for m in messages if m.get("role") == "assistant" and m.get("tool_calls")), None
            )
            if assistant is None or assistant["tool_calls"][0].get("thought_signature") != "sig123":
                raise RuntimeError("400: function call is missing a thought_signature")
            return ChatResult(content="done", tool_calls=[])

    evidence_item = EvidenceItem(
        id="route_deviation:1", type="route_deviation", trip_id=1, summary="dev", data={}, supports="rider", strength=0.5
    )

    async def fake_tool(trip_id=1):
        return evidence_item

    class FakeRegistry:
        def tool_specs(self):
            return []

        def get_tool(self, name):
            return SimpleNamespace(name=name, func=fake_tool)

    monkeypatch.setattr("app.agents.base.llm_client", FakeChat())
    monkeypatch.setattr("app.agents.base.registry", FakeRegistry())

    agent = RiderAdvocate()
    ctx = AgentContext(dispute_id=1, trip_id=1, category="route_deviation", claim_text="deviation")
    evidence, calls = await agent._gather_evidence(ctx, [], None, None)

    assert calls == 1
    assert len(evidence) == 1
    assert evidence[0].id == "route_deviation:1"
