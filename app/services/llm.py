import json
import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger("supportmesh.llm")

class LLMService:
    def __init__(self):
        api_key = settings.GROQ_API_KEY
        if self._is_placeholder_api_key(api_key):
            self.client = None
            logger.warning("GROQ_API_KEY is not set or is using a placeholder. Falling back to local mock responses.")
        else:
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url=settings.GROQ_BASE_URL
            )

    @staticmethod
    def _is_placeholder_api_key(api_key: str) -> bool:
        normalized = (api_key or "").strip().lower()
        return (
            not normalized
            or "your" in normalized
            or "placeholder" in normalized
            or normalized in {"changeme", "replace_me", "replace-me"}
        )

    async def analyze_ticket(
        self,
        customer_name: str,
        customer_tier: str,
        history: List[Dict[str, Any]],
        articles: List[Dict[str, Any]],
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        
        # Format history context
        history_str = "\n".join([
            f"- [{t.get('status')}] {t.get('subject')}: {t.get('body')} -> Drafted Response: {t.get('draft_response')}"
            for t in history
        ]) if history else "No previous support ticket history."

        # Format knowledge base context
        articles_str = "\n\n".join([
            f"Title: {art.get('title')}\nCategory: {art.get('category')}\nContent: {art.get('content')}"
            for art in articles
        ]) if articles else "No relevant knowledge base articles found."

        if not self.client:
            logger.info("Using mock response generator (Groq client not initialized).")
            return self._generate_mock_response(subject, body, customer_name, articles)

        # Define the tool schema for Groq API
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_support_ticket",
                    "description": "Analyze support ticket content, history, and retrieved knowledge base articles to categorize and draft responses.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "classification": {
                                "type": "string",
                                "description": "Classification category: billing, refunds, invoices, password reset, account access, login issues, VPN troubleshooting, product onboarding, feature usage, general support"
                            },
                            "draft_response": {
                                "type": "string",
                                "description": "A draft reply to the customer solving their problem using retrieved articles. Be polite and professional."
                            },
                            "confidence_score": {
                                "type": "number",
                                "description": "The confidence score for the analysis and resolution between 0.0 and 1.0"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["open", "pending", "resolved"],
                                "description": "The suggested status of the ticket"
                            }
                        },
                        "required": ["classification", "draft_response", "confidence_score", "status"]
                    }
                }
            }
        ]

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI support agent. Your job is to classify the support ticket, "
                    "suggest a status, and write a helpful draft response based on the "
                    "provided knowledge base articles and customer details."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Customer Name: {customer_name}\n"
                    f"Customer Account Tier: {customer_tier}\n\n"
                    f"Customer History:\n{history_str}\n\n"
                    f"Retrieved Articles:\n{articles_str}\n\n"
                    f"Ticket Subject: {subject}\n"
                    f"Ticket Body: {body}\n"
                )
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=messages,
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "analyze_support_ticket"}},
                temperature=0.2
            )
            
            tool_call = response.choices[0].message.tool_calls[0]
            result = json.loads(tool_call.function.arguments)
            logger.info(f"Successfully processed ticket with Groq. Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}. Falling back to mock response.")
            return self._generate_mock_response(subject, body, customer_name, articles)

    def _generate_mock_response(
        self,
        subject: str,
        body: str,
        customer_name: str,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        text = (subject + " " + body).lower()
        
        # Categorize
        classification = "general support"
        if "bill" in text or "charge" in text or "pricing" in text or "subscription" in text:
            classification = "billing"
        elif "refund" in text or "money back" in text or "cancel" in text:
            classification = "refunds"
        elif "invoice" in text or "receipt" in text:
            classification = "billing"
        elif "password" in text or "reset" in text:
            classification = "password reset"
        elif "login" in text or "signin" in text or "account" in text:
            classification = "account access"
        elif "vpn" in text or "connect" in text or "network" in text:
            classification = "technical troubleshooting"
        elif "onboard" in text or "setup" in text or "start" in text:
            classification = "onboarding"
        elif "feature" in text or "how do i" in text:
            classification = "product usage"

        # Try to locate a matching knowledge article
        matched_content = ""
        for art in articles:
            if art.get("category") == classification:
                matched_content = art.get("content")
                break
        if not matched_content and articles:
            matched_content = articles[0].get("content")

        if matched_content:
            draft_response = (
                f"Hi {customer_name},\n\n"
                f"Thanks for reaching out! Regarding your concern about '{subject}', here is how you can resolve this:\n\n"
                f"{matched_content}\n\n"
                f"Please let us know if this solves your issue, or if we can help you with anything else."
            )
        else:
            draft_response = (
                f"Hi {customer_name},\n\n"
                f"Thank you for contacting SupportMesh regarding '{subject}'. We've categorized this under '{classification}' "
                f"and our team is looking into it.\n\n"
                f"We will follow up with you shortly."
            )

        status = "resolved" if classification in ["password reset", "refunds", "billing"] else "open"

        return {
            "classification": classification,
            "draft_response": draft_response,
            "confidence_score": 0.92,
            "status": status
        }

# Singleton instance
llm_service = LLMService()
