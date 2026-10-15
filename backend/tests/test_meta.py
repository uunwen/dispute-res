import httpx

from app.main import app
from app.policies import load_policy_sections
from app.rules.engine import load_rules


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_meta_policies_returns_sections_and_precedents():
    async with _client() as client:
        resp = await client.get("/meta/policies")
    assert resp.status_code == 200
    sections = resp.json()
    assert sections
    for s in sections:
        assert {"id", "title", "text", "source"} <= s.keys()
        assert s["text"], f"section {s['id']} has empty text"
    precedents = [s for s in sections if s.get("tag") == "precedent"]
    assert precedents, "expected precedent-tagged sections"
    assert all(s["source"] == "precedent.md" for s in precedents)


def test_policy_sections_ids_are_unique():
    sections = load_policy_sections()
    ids = [s.id for s in sections]
    assert len(ids) == len(set(ids))


def test_rules_loader_returns_parsed_entries():
    rules = load_rules()
    assert rules
    for r in rules:
        assert r.id and r.category and r.outcome


async def test_meta_rules_endpoint():
    async with _client() as client:
        resp = await client.get("/meta/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert rules
    for r in rules:
        assert {"id", "category", "citation", "conditions", "outcome", "amount"} <= r.keys()


async def test_meta_settings_has_no_credentials():
    async with _client() as client:
        resp = await client.get("/meta/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data and "llm_mock" in data
    assert len(data["models"]) == 3
    for m in data["models"]:
        assert {"agent", "model", "purpose"} <= m.keys()
    for section in ("policy_numbers", "thresholds", "escalation"):
        assert section in data
        for entry in data[section]:
            assert {"key", "label", "value", "source"} <= entry.keys()

    blob = str(data).lower()
    for secret in ("api_key", "apikey", "password", "secret", "https://", "base_url", "token"):
        assert secret not in blob


async def test_list_disputes_includes_ruling_and_external_fields(seeded_session):
    async with _client() as client:
        resp = await client.get("/disputes")
    assert resp.status_code == 200
    data = resp.json()
    for d in data:
        for field in ("external_id", "confidence", "ruling_created_at", "llm_degraded"):
            assert field in d, f"missing field {field!r}"
