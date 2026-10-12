# Evaluation

From the repository root:

```bash
python eval/run_eval.py --offline   # no LLM or API key: retrieval + data sanity check, writes results_offline.md
python eval/run_eval.py             # full: runs the agent graph, needs an API key, writes results.md
```

- `golden.jsonl`: 20 items (7 rag, 5 tool, 6 multi_agent, 2 conversation) with `expected_sources`,
  `expected_tools`, `expected_agents`, `expected_root_cause` and `must_include`. Conversation items
  have `turns`; the last turn is scored. A `must_include` entry is a string or a list of accepted
  spellings (e.g. `["1.57", "1.6 km"]`); facts are specific so they cannot match by accident.
- Offline metrics: retrieval hit@4 and MRR on the 7 RAG items (expected sources = the defining
  documents); a data sanity check: for every route in `data/scenarios.json`, the runbook rules applied
  with the tool implementations must detect exactly the planted root cause (this validates the data, not
  the agents). Pass: hit@4 >= 0.8 and all routes. Exits non-zero on failure.
- Full metrics: agent selection accuracy, verification decision accuracy, tool selection (tools called
  by the Research and Analyst agents), root cause
  accuracy, must_include fact recall, source citation hit, Verifier approval rate, average steps and
  latency. All deterministic (no LLM-as-judge). Reports only (no pass threshold). `results.md` is written
  by a full run with an API key.
