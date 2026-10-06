# Using PolicyPal from Langflow

The project brief we were given included the source code of Langflow's **Chat Input** component. PolicyPal keeps all retrieval, guardrails and citation logic in the Flask service. This folder provides a small Langflow custom component that connects a Langflow flow to that service:

```text
Chat Input ──Message──▶ PolicyPal RAG ──Message──▶ Chat Output
                             │
                             └─ POST {api_url}/chat  {"question": <Chat Input text>, "session_id": <Chat Input session>}
```

## How the Chat Input component shaped the API

| Chat Input field | How PolicyPal handles it |
|---|---|
| `input_value` (the message text) | `POST /chat` accepts `input_value` as well as `question` |
| `session_id` | Accepted and echoed back; each question is still answered independently |
| `files` | Rejected with HTTP 400, because PolicyPal answers text questions only |
| `sender`, `sender_name`, `should_store_message` | Langflow-side settings; not needed by the API |

## Steps

1. Start PolicyPal (`python -m flask --app app run --port 5000`) or use the live URL <https://policypal-8u6n.onrender.com>.
2. In Langflow, create a blank flow and add **Chat Input** and **Chat Output**.
3. Add the component: **New Custom Component**, paste the contents of [`policypal_component.py`](policypal_component.py) and save. Alternatively, put this folder on `LANGFLOW_COMPONENTS_PATH`.
4. Connect **Chat Input → Chat Message** to **PolicyPal RAG → Question**, and **PolicyPal RAG → Answer** to **Chat Output**.
5. Set **PolicyPal URL** on the component. When Langflow runs in Docker and PolicyPal on the same computer, use `http://host.docker.internal:5000`.
6. Open the Playground and ask a policy question. The reply has the answer plus a "Sources" list with section links and snippets. The second output, **Citations**, returns the structured citations as Langflow `Data` objects.

## Testing

`tests/test_langflow_component.py` runs the component offline. It replaces the `lfx` classes with small stand-ins and sends the component's HTTP calls to the Flask test app, checking a cited answer, a refusal and an API error. The component has not yet been run inside a full Langflow installation; record the result in `ai-tooling.md` after you try it.
