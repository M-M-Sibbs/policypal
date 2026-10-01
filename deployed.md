# Deployment record

| Item | Value |
|---|---|
| Platform | Railway (Dockerfile build, `railway.json`) |
| Public URL | *Not deployed yet — add the Railway domain here after the first deploy* |
| Deployed commit | – |
| Health check | `GET /health` |
| Configuration | `EMBED_BACKEND=sentence-transformers`, `RERANK=1`, `LLM_PROVIDER=groq`, `LLM_MODEL=…`, `SCORE_THRESHOLD=…` |
| Cold start (first request after deploy/sleep) | – |
| Deployed latency p50 / p95 | – (run `python -m eval.run --url <public-url> --name railway-latency`) |

See README §6 for the deployment steps.
