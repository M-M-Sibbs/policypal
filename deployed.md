# Deployment

PolicyPal is deployed on Render (free web service, Docker).

| | |
|---|---|
| Live application | <https://policypal-8u6n.onrender.com> |
| Health check | <https://policypal-8u6n.onrender.com/health> |
| Policy management | <https://policypal-8u6n.onrender.com/admin> (admin token provided in the submission PDF) |
| Build files | `render.yaml`, `Dockerfile.render`, `requirements-lite.txt` |

The free instance sleeps after about 15 minutes without traffic. The first request after that takes roughly a minute while it wakes; later requests are fast.

## Configuration

| Setting | Value |
|---|---|
| Embeddings | ONNX `all-MiniLM-L6-v2-onnx` (index built into the image at build time) |
| LLM | Groq `openai/gpt-oss-20b`, temperature 0, 300 max tokens |
| Retrieval | `TOP_K=8`, `TOP_N=4`, `SCORE_THRESHOLD=0.30`, `RERANK=0` |
| Server | gunicorn, 1 worker, 4 threads |
| Secrets | `LLM_API_KEY` and `ADMIN_TOKEN` are Render environment variables; neither is in the repository |

## Verified on the live deployment

- `/health` returns `status: ok`, `index_ready: true`, 12 documents, 203 chunks, `embed_backend: onnx`, `llm_provider: groq`.
- `/api/policies` lists the 12 policies.
- Policy questions are answered with citations from provider `groq:openai/gpt-oss-20b`; out-of-scope questions are refused.

## Trying a policy update on the live site

1. Open `/admin` and sign in with the admin token.
2. Upload `examples/policy-updates/POL-02_paid_time_off_update.md` with **Replaces → POL-02**.
3. In the chat, ask *"How many unused PTO days can I carry over?"* — the answer changes from 5 to 8 days and cites POL-02 version 1.1.
4. Click **Reset to original policies**.

Uploads are kept on the container's temporary disk, so they also disappear when the service restarts or redeploys.

## Deployed latency

| Measurement | Result |
|---|---|
| Cold start (first request after sleep) | *record here* |
| p50 / p95 over 20 warm requests | *record here* — `python -m eval.run --url https://policypal-8u6n.onrender.com --name render-latency --latency-n 20 --delay-s 5` |
