"""PolicyPal RAG - a Langflow custom component.

Wire it into a flow as:   Chat Input  ->  PolicyPal RAG  ->  Chat Output

It takes the Message produced by Langflow's Chat Input component (the code in
the project brief), sends its text to PolicyPal's POST /chat endpoint, and
returns a Message whose text is the grounded answer followed by its sources.
All retrieval, guardrails and citation checks stay in the Flask service, so
the Langflow playground and the web UI always give the same answer.

Add it in Langflow via "New Custom Component" and paste this file, or place it
in a folder listed in LANGFLOW_COMPONENTS_PATH.
"""
from __future__ import annotations

import httpx

try:  # Langflow >= 1.6 (lfx package)
    from lfx.custom.custom_component.component import Component
    from lfx.io import IntInput, MessageInput, MessageTextInput, Output
    from lfx.schema.data import Data
    from lfx.schema.message import Message
except ImportError:  # older Langflow releases
    from langflow.custom import Component
    from langflow.io import IntInput, MessageInput, MessageTextInput, Output
    from langflow.schema import Data
    from langflow.schema.message import Message


class PolicyPalRAG(Component):
    display_name = "PolicyPal RAG"
    description = "Answer a policy question with citations using the PolicyPal Flask API."
    icon = "BookOpenCheck"
    name = "PolicyPalRAG"

    inputs = [
        MessageInput(
            name="input_value",
            display_name="Question",
            info="Connect the Chat Input component here.",
            required=True,
        ),
        MessageTextInput(
            name="api_url",
            display_name="PolicyPal URL",
            info="Base URL of the running PolicyPal service, e.g. http://localhost:5000 or https://policypal-8u6n.onrender.com.",
            value="http://localhost:5000",
        ),
        IntInput(
            name="timeout",
            display_name="Timeout (seconds)",
            value=60,
            advanced=True,
        ),
    ]
    outputs = [
        Output(display_name="Answer", name="answer", method="answer_response"),
        Output(display_name="Citations", name="citations", method="citations_data"),
    ]

    _result: dict | None = None

    async def _call(self) -> dict:
        if self._result is not None:
            return self._result
        message = self.input_value
        question = message.text if isinstance(message, Message) else str(message or "")
        session_id = getattr(message, "session_id", "") or ""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                self.api_url.rstrip("/") + "/chat",
                json={"question": question, "session_id": session_id},
            )
        try:
            body = resp.json()
        except ValueError:
            body = {"status": "provider_error", "message": f"PolicyPal returned HTTP {resp.status_code}."}
        self._result = body
        return body

    async def answer_response(self) -> Message:
        body = await self._call()
        if "answer" not in body:
            text = body.get("message", "PolicyPal could not answer right now.")
        else:
            lines = [body["answer"]]
            if body.get("citations"):
                lines.append("")
                lines.append("Sources:")
                base = self.api_url.rstrip("/")
                for c in body["citations"]:
                    lines.append(f"[{c['id']}] {c['title']} - {c['section']} ({base}{c['source_url']})")
                    lines.append(f'    "{c["snippet"]}"')
            text = "\n".join(lines)
        self.status = body.get("status", "")
        return Message(text=text)

    async def citations_data(self) -> list[Data]:
        body = await self._call()
        return [Data(data=c) for c in body.get("citations", [])]
