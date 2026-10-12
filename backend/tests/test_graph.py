"""Graph routing with a scripted LLM (no API key): multi-agent path, revisions, guards, memory."""
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import AIMessage

from app.agents import DraftAnswer, RouteDecision, Verdict
from app.config import Settings
from app.graph import build_graph, run_turn
from app.tools.tickets import TicketDraft

from .fakes import ScriptedLLM, tool_call

SETTINGS = Settings(_env_file=None, max_steps=8, max_revisions=2)

TICKET = TicketDraft(severity="P3", pci=205, neighbor_pci=145, site_name="STO-Norrmalm",
                     symptom="DL throughput below 600 Mbps on route R3",
                     evidence="avg 242 Mbps, SS-SINR 0.5 dB, neighbor 145 within 3 dB",
                     root_cause_id="RC6", recommended_action="PCI re-plan, RAN optimization team",
                     confidence="high")


def route(next_step, task="", verify=True, reason="test"):
    return RouteDecision(next=next_step, reason=reason, task=task, needs_verification=verify)


def diagnosis_script(verdicts):
    return {
        "RouteDecision": [route("analyst", "Collect evidence for route R3"),
                          route("research", "Runbook rules for RC6 and severity"),
                          route("answer")],
        "analyst": [
            tool_call("query_network_data", sql="SELECT AVG(dl_throughput_mbps), AVG(ss_sinr_db) "
                                                "FROM measurements WHERE route_id = 'R3'"),
            tool_call("network_calculator", call_id="c2", operation="pci_mod30", pci_a=205, pci_b=145),
            AIMessage("R3: avg 242 Mbps, SINR 0.5 dB; PCI 205 and 145 share PCI mod 30 = 25."),
        ],
        "research": [tool_call("search_knowledge_base", query="PCI mod 30 conflict confirm"),
                     AIMessage("RC6 confirmed by equal PCI mod 30 (runbook_interference.md > How to tell RC4 and RC6 apart).")],
        "DraftAnswer": [DraftAnswer(answer="Root cause: RC6 on PCI 205 and 145. Severity P3.",
                                    sources=["runbook_interference.md > How to tell RC4 and RC6 apart",
                                             "invented.md > Nowhere"],
                                    root_cause_id="RC6", proposed_ticket=TICKET)],
        "Verdict": verdicts,
    }


def test_multi_agent_diagnosis_path():
    llm = ScriptedLLM(diagnosis_script([Verdict(verdict="approve", feedback="ok")]))
    out = run_turn(build_graph(llm, SETTINGS), "t1", "Diagnose route R3")

    agents = [t["agent"] for t in out["trace"]]
    assert {"Supervisor", "Analyst", "Research", "Answer", "Verifier"} <= set(agents)
    tools = [t["detail"].split("(")[0] for t in out["trace"] if t["type"] == "tool_call"]
    assert tools == ["query_network_data", "network_calculator", "search_knowledge_base"]
    # Real tools ran: the calculator result is in the trace.
    assert any('"conflict": true' in t["detail"] for t in out["trace"])
    # Hallucinated citation is dropped; only retrieved sources are returned.
    assert out["sources"] == ["runbook_interference.md > How to tell RC4 and RC6 apart"]
    assert out["proposed_ticket"]["root_cause_id"] == "RC6"
    assert out["approved"] is True and out["root_cause_id"] == "RC6"
    assert out["steps"] == 3
    assert llm.remaining() == {}


def test_revision_then_approve_goes_back_to_supervisor():
    script = diagnosis_script([Verdict(verdict="revise", feedback="Add the SINR value"),
                               Verdict(verdict="approve", feedback="ok")])
    script["RouteDecision"].append(route("answer", reason="Findings already contain SINR"))
    script["DraftAnswer"].append(script["DraftAnswer"][0])
    llm = ScriptedLLM(script)
    out = run_turn(build_graph(llm, SETTINGS), "t2", "Diagnose route R3")
    verdicts = [t["detail"] for t in out["trace"] if t["type"] == "verdict"]
    assert verdicts[0].startswith("revise") and verdicts[1].startswith("approve")
    # The feedback reached the Supervisor's prompt.
    supervisor_prompts = [m[1].content for key, m in llm.calls if key == "RouteDecision"]
    assert "Add the SINR value" in supervisor_prompts[-1]
    assert out["proposed_ticket"] is not None


def test_revision_limit_adds_caveat_and_withholds_ticket():
    revise = Verdict(verdict="revise", feedback="Severity not justified")
    script = diagnosis_script([revise] * 3)
    script["RouteDecision"] += [route("answer")] * 2
    script["DraftAnswer"] *= 3
    out = run_turn(build_graph(ScriptedLLM(script), SETTINGS), "t3", "Diagnose route R3")
    assert "Caveat" in out["answer"] and out["proposed_ticket"] is None
    assert len([t for t in out["trace"] if t["type"] == "verdict"]) == 3


def test_definition_goes_to_research_only_without_verifier():
    llm = ScriptedLLM({
        "RouteDecision": [route("research", "Define PCI mod 30", verify=False), route("answer", verify=False)],
        "research": [AIMessage("PCI mod 30 sets the uplink DMRS sequence group.")],
        "DraftAnswer": [DraftAnswer(answer="PCI mod 30 ...", sources=[])],
    })
    out = run_turn(build_graph(llm, SETTINGS), "t4", "What is PCI mod 30?")
    agents = {t["agent"] for t in out["trace"]}
    assert "Analyst" not in agents and "Verifier" not in agents
    assert out["approved"] is None and out["proposed_ticket"] is None


def test_step_guard_forces_answer():
    llm = ScriptedLLM({
        "RouteDecision": [route("research", "search again")] * 2,
        "research": [AIMessage("nothing new")] * 2,
        "DraftAnswer": [DraftAnswer(answer="Partial answer.")],
        "Verdict": [Verdict(verdict="approve", feedback="ok")],
    })
    out = run_turn(build_graph(llm, Settings(_env_file=None, max_steps=2)), "t5", "Loop forever")
    assert any(t["type"] == "guard" for t in out["trace"])
    assert out["answer"] == "Partial answer."


def test_tool_errors_are_returned_to_the_agent():
    llm = ScriptedLLM({
        "RouteDecision": [route("analyst", "Count cells", verify=False), route("answer", verify=False)],
        "analyst": [tool_call("query_network_data", sql="DROP TABLE cells"),
                    tool_call("create_ticket", call_id="c2", severity="P1"),
                    AIMessage("The query was rejected.")],
        "DraftAnswer": [DraftAnswer(answer="Could not query.")],
    })
    out = run_turn(build_graph(llm, SETTINGS), "t6", "Delete the cells table")
    details = [t["detail"] for t in out["trace"] if t["type"] == "tool_call"]
    assert "Error: only SELECT" in details[0]
    # The Analyst has no create_ticket permission.
    assert "not available to this agent" in details[1]


def test_follow_up_uses_conversation_memory():
    llm = ScriptedLLM({
        "RouteDecision": [route("answer", verify=False), route("research", "Severity for RC6 on route R3"),
                          route("answer")],
        "DraftAnswer": [DraftAnswer(answer="Route R3 shows RC6."), DraftAnswer(answer="P3 Minor.")],
        "research": [AIMessage("P3 Minor: single-route degradation with a known cause.")],
        "Verdict": [Verdict(verdict="approve", feedback="ok")],
    })
    graph = build_graph(llm, SETTINGS)
    run_turn(graph, "thread-a", "Diagnose route R3")
    out = run_turn(graph, "thread-a", "And what severity should that be?")
    second_prompt = [m for key, m in llm.calls if key == "RouteDecision"][1][1].content
    assert "Copilot: Route R3 shows RC6." in second_prompt
    # The Verifier also sees the earlier turn, so facts from it count as evidence.
    verifier_prompt = [m for key, m in llm.calls if key == "Verdict"][0][1].content
    assert "Copilot: Route R3 shows RC6." in verifier_prompt
    assert out["answer"] == "P3 Minor."
    # Per-turn fields were reset: only the second turn's trace is returned.
    assert sum(t["type"] == "answer" for t in out["trace"]) == 1
    state = graph.get_state({"configurable": {"thread_id": "thread-a"}}).values
    assert len(state["messages"]) == 4


def test_unknown_root_cause_is_accepted():
    assert DraftAnswer(answer="No rule explains it.", root_cause_id="unknown").root_cause_id == "unknown"


def test_invalid_structured_output_is_retried_then_falls_back():
    bad = OutputParserException("next must be research, analyst or answer")
    llm = ScriptedLLM({
        "RouteDecision": [bad, bad],                         # Supervisor: two invalid outputs -> answer
        "DraftAnswer": [None, DraftAnswer(answer="Hello.")],  # Answer: one retry succeeds
    })
    out = run_turn(build_graph(llm, SETTINGS), "t7", "Hi")
    assert out["answer"] == "Hello."
    assert any(t["type"] == "guard" and "invalid" in t["detail"] for t in out["trace"])
    assert llm.remaining() == {}


def test_invalid_verdict_gives_caveat_not_an_error():
    llm = ScriptedLLM({
        "RouteDecision": [route("answer")],
        "DraftAnswer": [DraftAnswer(answer="R3 is RC6.", root_cause_id="RC6", proposed_ticket=TICKET)],
        "Verdict": [None, None],
    })
    out = run_turn(build_graph(llm, SETTINGS), "t8", "Diagnose route R3")
    assert "Caveat" in out["answer"] and out["proposed_ticket"] is None
    assert llm.remaining() == {}


def test_rewrite_after_revise_is_rechecked_even_without_ticket():
    from app.graph import route_after_answer
    state = {"needs_verification": False, "draft": {"proposed_ticket": None}, "approved": False}
    assert route_after_answer(state) == "verifier"
    assert route_after_answer(dict(state, approved=None)) == "finalize"
