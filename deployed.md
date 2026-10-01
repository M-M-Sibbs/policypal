# Deployment record

| Item | Value |
|---|---|
| Platform | Render free web service (Docker, `render.yaml` + `Dockerfile.render`) |
| Public URL | *Add the onrender.com URL here after the first deploy* |
| Deployed commit | – |
| Health check | `GET /health` |
| Configuration | `EMBED_BACKEND=hash`, `RERANK=0`, `LLM_PROVIDER=groq`, `LLM_MODEL=llama-3.1-8b-instant`, `SCORE_THRESHOLD=0.12` (lightweight build for 512 MB RAM) |
| Cold start (first request after sleep) | – |
| Deployed latency p50 / p95 | – (run `python -m eval.run --url <public-url> --name render-latency`) |

The deployed build uses lexical (hash) retrieval because the free plan cannot hold the embedding and re-ranking models. Local runs use the full bge + cross-encoder pipeline. Report both configurations in design-and-evaluation.md.

See README §6 for the deployment steps (Render, and Railway as an alternative).
