# NOC Copilot frontend

React chat UI for NOC Copilot (Vite, React 18, TypeScript, plain CSS).

## Run

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (port matches the backend CORS allow-list)
npm run build      # type check (tsc) + production bundle in dist/
npm run preview    # serve dist/ on http://localhost:5173
```

The backend must be running (see the root README). Its URL is read from `VITE_API_URL`,
default `http://localhost:8000`:

```bash
VITE_API_URL=http://localhost:8000 npm run dev
```

## What it shows

- Header with a backend status dot (`GET /health`, polled every 30 s) and a "New conversation" button
  (new `session_id`, used by the backend as the conversation thread id).
- Example questions grouped by RAG, tool use and multi-agent.
- Each answer: markdown text, source chips (`doc.md > Section`), and a collapsible "How I got this"
  panel with the agent trace (routing reasons, tool calls, verifier verdict).
- Proposed tickets with Approve / Dismiss. Approve calls `POST /api/tickets`; nothing is created
  without that click.
- API errors (no API key, backend down) are shown in the thread.

## Structure

```
src/
  main.tsx                     entry point
  App.tsx                      layout, session, message list, composer
  api.ts                       fetch wrapper: /health, /api/chat, /api/tickets
  types.ts                     API types (mirror backend/app/api.py)
  styles.css                   all styles
  components/
    ChatMessage.tsx            user, assistant and error messages
    TracePanel.tsx             "How I got this" trace
    TicketCard.tsx             proposed ticket with human approval
    ExampleQuestions.tsx       example questions by category
    AgentBadge.tsx             agent-colored label
```
