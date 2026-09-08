# AI Support Agent

A full-stack, multi-tenant-style **AI customer support platform** for a service business (built around a salon/spa, "Serenity Salon & Spa," but generic enough for any appointment-based business). It combines a **RAG knowledge base**, a **multi-agent LLM orchestrator**, **appointment booking**, and a **real-time voice agent** — reachable from a browser, and now from a real phone call.

This README is the entry point. See the other docs in this folder for details:

| Doc | Covers |
|---|---|
| [`PROJECT_STRUCTURE.md`](./PROJECT_STRUCTURE.md) | Folder-by-folder tour of both the backend and frontend |
| [`TECH_STACK.md`](./TECH_STACK.md) | Every major library/service used and why |
| [`DATABASE_ARCHITECTURE.md`](./DATABASE_ARCHITECTURE.md) | Tables, relationships, migrations |
| [`HOW_TO_RUN.md`](./HOW_TO_RUN.md) | Local setup, env vars, running both apps |
| [`VOICE_AND_TELEPHONY.md`](./VOICE_AND_TELEPHONY.md) | The real-time voice agent (browser) and phone-call (Exotel) integration in depth |
| [`API_REFERENCE.md`](./API_REFERENCE.md) | Every REST/WebSocket endpoint, grouped by area |

---

## What this project does

A business admin configures their services, staff, opening hours, and knowledge base (uploaded documents + FAQs/policies) through an admin dashboard. Customers then interact with an AI assistant through:

- **A text chat widget** embedded on the business's site
- **A real-time voice call** from the browser (talk to the AI like a phone call, no push-to-talk)
- **A real phone call** to a business phone number (via Exotel), talking to the exact same AI agent

Under the hood, every channel (chat / browser voice / phone) is driven by the same **multi-agent orchestrator**, which:

1. Identifies the customer (by email for chat/browser voice, automatically by Caller ID for phone when possible)
2. Routes each message to one of three specialist agents:
   - **Knowledge Agent** — answers questions using RAG over uploaded documents + FAQs/policies/business info
   - **Booking Agent** — books, reschedules, or cancels appointments, always restating details and getting explicit confirmation before doing anything destructive
   - **Support Agent** — hands off to a human when the AI can't help, creating a ticket the admin can see and resolve
3. Persists the whole conversation so an admin can review it, regardless of which channel it came from

## Key capabilities

- **RAG knowledge base** — PDFs/DOCX are chunked, embedded (`sentence-transformers`), and stored in Postgres via `pgvector`; answers are grounded in retrieved chunks plus structured business data (services, hours, FAQs, policies).
- **Multi-agent architecture** — a lightweight orchestrator classifies intent and delegates to Knowledge / Booking / Support agents, each with their own tool-calling loop (`tool_loop.py`) against Groq's Llama models.
- **Appointment booking** — real slot availability against staff schedules, opening hours, and holidays; book/reschedule/cancel, all requiring explicit confirmation.
- **Real-time voice (browser)** — the browser streams the mic directly to Deepgram STT, gets live transcripts, and plays back streaming Deepgram TTS audio — with barge-in (interrupt the AI while it's talking) and end-of-speech detection.
- **Real phone calls (Exotel)** — the exact same agent pipeline, but with the *backend* bridging a live phone call's audio to Deepgram STT/TTS, so a customer can just call a number.
- **Unclear-speech handling** — low-confidence or filler-only transcripts trigger a clarification question instead of being acted on; repeated failures escalate to a human. Booking/reschedule/cancel actions always require an explicit "yes."
- **Human handoff** — either channel can escalate to a support ticket (keyword/LLM-detected frustration, repeated failures, unclear speech, or — on phone calls — pressing `0`).
- **Full admin dashboard** — manage services, staff, business info, holidays, chatbot persona/voice config, knowledge base documents, customers, appointments, conversations (with the ability to resolve/reopen), and basic analytics.

## Status

This documents the project as of the most recent work session, which added:
1. Unclear-speech detection + clarification/escalation flow for the browser voice channel
2. Full phone-call (PSTN) support via Exotel's AgentStream Voicebot Applet, reusing the same agent pipeline

See [`VOICE_AND_TELEPHONY.md`](./VOICE_AND_TELEPHONY.md) for the full design of both.
