# Using PolicyPal from Langflow

The project brief included Langflow's **Chat Input** component. PolicyPal keeps all retrieval, guardrails and citation logic in the Flask service, and this folder provides a small Langflow custom component that connects a Langflow flow to it:

```text
Chat Input  ──Message──▶  PolicyPal RAG  ──Message──▶  Chat Output
                               │
                               └─ POST {api_url}/chat  {"question": <Chat Input text>, "session_id": ...}
```

## Steps

1. Start PolicyPal (`flask --app app run --port 5000`) or use your Railway URL.
2. In Langflow, create a blank flow and add **Chat Input** and **Chat Output**.
3. Add the component: **New Custom Component**, replace the code with the contents of [`policypal_component.py`](policypal_component.py), and save. (Alternatively, put this folder on `LANGFLOW_COMPONENTS_PATH`.)
4. Connect **Chat Input → Chat Message** to **PolicyPal RAG → Question**, and **PolicyPal RAG → Answer** to **Chat Output**.
5. Set **PolicyPal URL** on the component (default `http://localhost:5000`; when Langflow runs in Docker use `http://host.docker.internal:5000`).
6. Open the Playground and ask a policy question. The reply contains the answer and a "Sources" list with section links and snippets. The second output, **Citations**, returns the structured citation list as Langflow `Data` objects.

## Notes

- `/chat` accepts both `question` and Langflow's `input_value` field, so a raw Chat Input payload can also be posted directly.
- Chat Input options such as *Store Messages* only affect Langflow's own history; PolicyPal answers each question independently.
- File attachments from Chat Input are not supported (the API returns HTTP 400 if `files` is non-empty); the component sends text only.
- The component was written against the `lfx` component API used by the supplied Chat Input code (with a fallback import for older Langflow versions). It has not yet been run in a Langflow installation; verify it once and record the result in `ai-tooling.md`.
