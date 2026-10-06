# Free deployment

Everything below runs on free tiers. No credit card is needed.

| Part | Host | Notes |
|---|---|---|
| Postgres + pgvector | [Neon](https://neon.tech) | Free 0.5 GB. The migration runs `CREATE EXTENSION vector` itself. |
| FastAPI backend | [Hugging Face Spaces](https://huggingface.co/spaces) (Docker, CPU basic) | Free 2 vCPU / 16 GB RAM, which fits the embedding model and reranker. It sleeps after about 48 h without traffic, and the first request after that takes around a minute. |
| React frontend | [Vercel](https://vercel.com) | Static build from `frontend/`, rebuilt on every push to `main`. |

Ingestion runs inline (no Redis or Celery needed). Uploaded files sit on the Space's temporary disk,
but chunks and embeddings live in Neon, so chat and summaries keep working after a restart.

## 1. Database (Neon)

1. Sign in at https://console.neon.tech with GitHub and create a project (Postgres 16 or newer, nearest region).
2. Copy the connection string (`postgresql://...neon.tech/neondb?sslmode=require`).
   The backend changes `postgresql://` to `postgresql+psycopg://` automatically.

## 2. Backend (Hugging Face Space)

1. Sign up at https://huggingface.co. Under **Settings → Access Tokens**, create a token with **Write** access.
2. Log in once and upload the backend from the repo root:

   ```powershell
   uvx --from huggingface_hub hf auth login     # paste the write token
   uv run --no-project --with huggingface_hub python scripts/deploy_hf_space.py <hf-user>/techprep-ai-api
   ```

3. In the Space, open **Settings → Variables and secrets** and add these as **secrets**:

   | Name | Value |
   |---|---|
   | `ENV` | `prod` |
   | `DATABASE_URL` | the Neon connection string |
   | `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `GEMINI_API_KEY` | your Gemini key |
   | `GROQ_API_KEY` | your Groq key |
   | `CORS_ORIGINS` | your Vercel URL, e.g. `https://techprep-ai.vercel.app` (no trailing slash) |
   | `WARMUP_MODELS` | `true` |
   | `LOG_JSON` | `true` |

   The Space restarts, runs `alembic upgrade head` against Neon, and serves on port 8000.
   Check `https://<hf-user>-techprep-ai-api.hf.space/health`.

To redeploy after backend changes, run the `deploy_hf_space.py` command again.

## 3. Frontend (Vercel)

1. Sign in at https://vercel.com with GitHub. Click **Add New → Project** and import `TechPrep-AI`.
2. Set **Root Directory** to `frontend`. The Vite preset fills in the build command (`npm run build`) and the output folder (`dist`).
3. Add these environment variables:

   | Name | Value |
   |---|---|
   | `VITE_API_URL` | `https://<hf-user>-techprep-ai-api.hf.space` |
   | `VITE_DEMO_EMAIL` | `demo@techprep.ai` (optional, shows a "Try the demo" button) |
   | `VITE_DEMO_PASSWORD` | the demo password |

4. Deploy. If the Vercel URL is different from what you put in `CORS_ORIGINS`, update the secret on the Space.

## 4. Demo account with sample notes

Run this from your laptop. It embeds the sample corpus locally and writes it straight to Neon:

```powershell
cd backend
$env:DATABASE_URL = "<neon connection string>"
uv run alembic upgrade head
uv run python -m app.cli create-user demo@techprep.ai "<demo password>"
uv run python -m app.cli seed-sample demo@techprep.ai
Remove-Item Env:DATABASE_URL
```

The demo account is shared, so anyone can add or delete its documents. Run `seed-sample` again
to restore the sample notes (it skips files that are already there).
