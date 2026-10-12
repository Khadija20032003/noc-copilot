"""API endpoints with the graph replaced by a scripted one (no API key)."""
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.agents import DraftAnswer, RouteDecision
from app.api import get_graph
from app.config import Settings
from app.graph import build_graph
from app.main import app

from .fakes import ScriptedLLM

TICKET = {"severity": "P3", "pci": 205, "neighbor_pci": 145, "site_name": "STO-Norrmalm",
          "symptom": "DL throughput below 600 Mbps", "evidence": "avg 242 Mbps", "root_cause_id": "RC6",
          "recommended_action": "PCI re-plan (RAN optimization team)", "confidence": "high"}


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_chat_without_api_key_returns_clear_error(monkeypatch):
    monkeypatch.setattr("app.llm.get_settings", lambda: Settings(_env_file=None, llm_provider="openai", openai_api_key="", anthropic_api_key=""))
    get_graph.cache_clear()
    with TestClient(app) as client:
        r = client.post("/api/chat", json={"session_id": "s", "message": "hi"})
    assert r.status_code == 503
    assert r.json()["error"] == "llm_not_configured" and "OPENAI_API_KEY" in r.json()["detail"]


def test_chat_contract_with_scripted_graph():
    llm = ScriptedLLM({
        "RouteDecision": [RouteDecision(next="research", reason="definition", task="Define RC7",
                                        needs_verification=False),
                          RouteDecision(next="answer", reason="done", needs_verification=False)],
        "research": [AIMessage("RC7 is high UE speed above 40 km/h.")],
        "DraftAnswer": [DraftAnswer(answer="RC7 means high UE speed (above 40 km/h).")],
    })
    app.dependency_overrides[get_graph] = lambda: build_graph(llm)
    try:
        with TestClient(app) as client:
            r = client.post("/api/chat", json={"session_id": "s1", "message": "What is RC7?"})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"answer", "sources", "trace", "proposed_ticket", "verified"}
    assert body["answer"].startswith("RC7") and body["proposed_ticket"] is None
    assert body["verified"] is None  # simple definition: the Verifier is skipped
    assert all(set(t) == {"agent", "type", "detail"} for t in body["trace"])


def test_chat_validates_input():
    app.dependency_overrides[get_graph] = lambda: None
    try:
        with TestClient(app) as client:
            assert client.post("/api/chat", json={"session_id": "", "message": "x"}).status_code == 422
            assert client.post("/api/chat", json={"session_id": "s"}).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_ticket_approval_flow(tickets_file):
    with TestClient(app) as client:
        assert client.get("/api/tickets").json() == []
        stored = client.post("/api/tickets", json=TICKET).json()
        assert stored["id"].startswith("NT-") and stored["status"] == "open"
        assert client.get("/api/tickets").json()[0]["id"] == stored["id"]
        bad = dict(TICKET, severity="P9")
        assert client.post("/api/tickets", json=bad).status_code == 422
