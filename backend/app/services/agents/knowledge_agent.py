from sqlalchemy.orm import Session

from app.services.agents.shared_context import admin_config, customer_context, tone_instructions, date_reference_table
from app.services.agents.tool_loop import AgentReply, ToolCallingAgent
from app.services.business_lookup_service import BusinessLookupService
from app.services.vector_store import get_vector_store

SYSTEM_PROMPT_TEMPLATE = """[ROLE] You are the Knowledge Agent for {business_name}'s front-desk assistant — a {business_description}. You handle questions ABOUT the business: services, pricing, opening hours, holidays/closures, policies, FAQs, location, and contact details. You do NOT book, reschedule, or cancel appointments — if the customer clearly wants to take a booking action, just acknowledge it naturally and let the system route the conversation there behind the scenes; don't attempt it yourself, don't invent a confirmation, and don't name any internal agent or system when you hand it off.
[TONE — Admin>Chatbot Config, "{tone}"] {tone_instructions}
[CUSTOMER] {customer_context}

[DATES - server clock, use verbatim; never compute a weekday/relative date yourself]
{date_reference_table}

Currency: INR (Rs.).

[TOOL] answer_business_question — your only source of truth. It checks the admin's database FIRST (business details, opening hours, holidays, FAQs, policies) and only falls back to the uploaded-documents knowledge base if nothing structured matches. ALWAYS call it before answering any factual question — never answer from memory or assumption.

[RULES]
1. Never invent services, prices, hours, holidays, addresses, or policy details — only state what answer_business_question actually returned.
2. If answer_business_question returns "source": "database", that is the admin's authoritative, current answer — treat it as final and don't hedge or second-guess it.
3. If it returns "source": "uploaded_documents", it came from a document the admin uploaded, not a live database field — you can still answer confidently, but if the document seems ambiguous or outdated, invite the customer to double check with the business directly.
4. If it finds nothing at all, say so plainly and either offer to help them book/check an appointment (if it's actually a booking question) or suggest they contact the business directly — never guess, and never name any internal agent or system.
5. Keep replies to about {reply_word_budget} words. Be direct and warm, no padding. Vary your phrasing turn to turn.
6. Never mention "tools", "functions", "database", "RAG", or other internal system details to the customer — you're simply "the assistant" to them.
7. If the request is entirely unrelated to {business_name}, politely decline and steer back.
8. You cannot connect the customer to a human, schedule a callback, or transfer them to live chat - you have no such tool. If they're asking for that, don't claim to do it or promise someone will reach out; that only happens automatically when they clearly state they want a person, which is handled outside this conversation. Just say plainly you can't do that here and offer to keep helping directly.

[FALLBACK] If you genuinely cannot help, adapt this naturally rather than reciting verbatim: "{fallback_message}"
"""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "answer_business_question",
            "description": (
                "Look up information about the business itself - services, pricing, hours, "
                "holidays/closures, policies, location, FAQs. Checks the admin's database "
                "first, and only falls back to uploaded documents if nothing matches there."
            ),
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
]


class KnowledgeAgent(ToolCallingAgent):
    agent_name = "knowledge"
    def __init__(self, db: Session, customer=None) -> None:
        super().__init__()
        self.db = db
        self.customer = customer
        self.lookup = BusinessLookupService(db)
        self.vector_store = get_vector_store()
        self._fallback_message = "I couldn't quite complete that - could you tell me more about what you need?"

    def system_prompt(self) -> str:
        cfg = admin_config(self.db)
        self._fallback_message = cfg["fallback_message"]
        reply_budget = max(20, cfg["reply_word_budget"] - 20)
        return SYSTEM_PROMPT_TEMPLATE.format(
            business_name=cfg["business_name"],
            business_description=cfg["business_description"],
            tone=cfg["tone"],
            tone_instructions=tone_instructions(cfg),
            customer_context=customer_context(self.customer),
            date_reference_table=date_reference_table(),
            reply_word_budget=f"{reply_budget}-{cfg['reply_word_budget']}",
            fallback_message=cfg["fallback_message"],
        )

    def tool_schemas(self) -> list[dict]:
        return TOOL_SCHEMAS

    def fallback_message(self) -> str:
        return self._fallback_message

    def dispatch(self, name: str, args: dict) -> dict:
        if name != "answer_business_question":
            return {"error": f"Unknown tool '{name}'."}
        return self.answer_business_question(args["question"])

    def answer_business_question(self, question: str) -> dict:
        """DB-first, then RAG fallback. This is the one place that decides
        whether the admin's structured data already answers the question."""
        from app.models.knowledge_base import Business

        business = self.db.query(Business).first()
        db_answer = self.lookup.answer(business, question)
        if db_answer:
            return {"context": db_answer, "source": "database"}

        hits = self.vector_store.search(question)
        if not hits:
            return {"context": "No matching information found in the knowledge base."}
        return {
            "context": "\n\n".join(h["text"] for h in hits),
            "source": "uploaded_documents",
            "_sources": hits,
        }

    def handle(self, question: str, history: list[dict]) -> AgentReply:
        return self.run(question, history)