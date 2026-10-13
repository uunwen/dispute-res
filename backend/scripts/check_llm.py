import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from pydantic import BaseModel

from app.config import settings
from app.llm.embeddings import embeddings

GET_TIME_TOOL = {
    "type": "function",
    "function": {
        "name": "get_time",
        "description": "Return the current UTC time as an ISO 8601 string.",
        "parameters": {"type": "object", "properties": {}},
    },
}


class _Structured(BaseModel):
    answer: str
    confidence: float


def _get_time() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _echo_assistant(message: dict) -> dict:
    """Rebuild an assistant message the same way the advocates do: id/type/function
    plus any provider-specific extra fields (e.g. thought_signature) echoed verbatim."""
    tool_calls = []
    for tc in message.get("tool_calls") or []:
        extra = {k: v for k, v in tc.items() if k not in ("id", "type", "function")}
        tool_calls.append(
            {
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]},
                **extra,
            }
        )
    return {"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls}


def _has_thinking(tool_calls) -> bool:
    for tc in tool_calls or []:
        if any(k not in ("id", "type", "function") for k in tc):
            return True
    return False


def _execute_tool(name: str, args: dict) -> dict:
    if name == "get_time":
        return {"time": _get_time()}
    return {"error": f"unknown tool: {name}"}


async def main() -> None:
    base = settings.llm_base_url.rstrip("/")
    chat_url = f"{base}/chat/completions"
    embed_base = settings.embedding_base_url or settings.llm_base_url
    embed_url = f"{embed_base.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
    json_headers = {**headers, "Content-Type": "application/json"}

    print("== LLM check ==")
    print(f"LLM_BASE_URL    : {settings.llm_base_url}")
    print(f"LLM_MODEL       : {settings.llm_model}")
    print(f"EMBEDDING_MODEL : {settings.embedding_model}")
    print(f"EMBEDDING_DIM   : {settings.embedding_dim}")
    print(f"LLM_MOCK        : {settings.llm_mock}")
    print(f"API key set     : {'yes' if settings.llm_api_key else 'no'}")

    results: dict[str, bool] = {}
    thinking = False

    # 1. list models
    print("\n[1/6] GET /models")
    model_ids: list[str] = []
    ok = True
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.get(f"{base}/models", headers=headers)
        if resp.status_code != 200:
            ok = False
            print(f"  FAIL: HTTP {resp.status_code}: {resp.text[:300]}")
        else:
            model_ids = [m.get("id") for m in resp.json().get("data", [])]
            for m in model_ids:
                print(f"  - {m}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  FAIL: {exc}")
    results["models"] = ok

    # 2. single chat
    print("\n[2/6] POST /chat/completions (single turn)")
    ok = True
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                chat_url,
                headers=json_headers,
                json={"model": settings.llm_model, "messages": [{"role": "user", "content": "Say hi in one word."}]},
            )
        if resp.status_code != 200:
            ok = False
            print(f"  FAIL: HTTP {resp.status_code}: {resp.text[:300]}")
        else:
            print(f"  PASS: {resp.json()['choices'][0]['message']['content']!r}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  FAIL: {exc}")
    results["chat"] = ok

    # 3. two-turn tool calling
    print("\n[3/6] tool calling (two turns)")
    ok = True
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            resp1 = await http.post(
                chat_url,
                headers=json_headers,
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": "What is the current UTC time? Use the get_time tool."}],
                    "tools": [GET_TIME_TOOL],
                    "tool_choice": "auto",
                },
            )
        if resp1.status_code != 200:
            ok = False
            print(f"  FAIL (turn 1): HTTP {resp1.status_code}: {resp1.text[:300]}")
        else:
            msg1 = resp1.json()["choices"][0]["message"]
            tool_calls = msg1.get("tool_calls") or []
            if not tool_calls:
                ok = False
                print("  FAIL: model did not emit a tool call")
            else:
                thinking = thinking or _has_thinking(tool_calls)
                echoed = _echo_assistant(msg1)
                tool_results = []
                for tc in tool_calls:
                    name = tc["function"]["name"]
                    args = json.loads(tc["function"].get("arguments") or "{}")
                    out = _execute_tool(name, args)
                    tool_results.append(
                        {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(out)}
                    )
                messages2 = [{"role": "user", "content": "What is the current UTC time? Use the get_time tool."}] + [echoed] + tool_results
                async with httpx.AsyncClient(timeout=60) as http:
                    resp2 = await http.post(
                        chat_url, headers=json_headers, json={"model": settings.llm_model, "messages": messages2}
                    )
                if resp2.status_code != 200:
                    ok = False
                    print(f"  FAIL (turn 2): HTTP {resp2.status_code}: {resp2.text[:300]}")
                else:
                    final = resp2.json()["choices"][0]["message"]["content"]
                    print(f"  PASS: final answer {final!r}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  FAIL: {exc}")
    results["tools"] = ok

    # 4. structured output
    print("\n[4/6] structured output")
    ok = True
    try:
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                chat_url,
                headers=json_headers,
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "user", "content": 'Return a JSON object with "answer" (string) and "confidence" (number 0-1).'}
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
        if resp.status_code != 200:
            ok = False
            print(f"  FAIL: HTTP {resp.status_code}: {resp.text[:300]}")
        else:
            content = resp.json()["choices"][0]["message"]["content"]
            _Structured.model_validate_json(content)
            print(f"  PASS: {content!r}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        print(f"  FAIL: {exc}")
    results["structured"] = ok

    # 5. embeddings (dimension must equal EMBEDDING_DIM)
    print("\n[5/6] embeddings")
    ok = True
    note = ""
    try:
        vecs = await embeddings.embed_texts(["hello"])
        dim = len(vecs[0]) if vecs else 0
        note = (
            f"provider={embeddings.active_provider} model={embeddings.active_model} "
            f"dim={dim} (EMBEDDING_DIM={settings.embedding_dim})"
        )
        if dim != settings.embedding_dim:
            ok = False
            print(f"  FAIL: dimension {dim} != EMBEDDING_DIM {settings.embedding_dim}")
        elif embeddings.fallback_reason:
            print(f"  PASS (fastembed fallback): {note} — reason: {embeddings.fallback_reason}")
        else:
            print(f"  PASS: {note}")
    except Exception as exc:  # noqa: BLE001
        ok = False
        note = f"failed: {exc}"
        print(f"  FAIL: {exc}")
    results["embeddings"] = ok

    # 6. summary
    required = ["chat", "tools", "structured"]
    failed = [k for k in required if not results[k]]

    print("\n== Results ==")
    for key in ("models", "chat", "tools", "structured", "embeddings"):
        print(f"  [{'PASS' if results.get(key) else 'FAIL'}] {key}")
    print(f"Model           : {settings.llm_model}")
    print(f"Thinking model  : {'yes' if thinking else 'no'}")

    if failed:
        print(f"\nRequired steps failed: {', '.join(failed)}")
        sys.exit(1)
    print("\nAll required steps passed.")


if __name__ == "__main__":
    asyncio.run(main())
