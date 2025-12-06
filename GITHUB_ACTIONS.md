# GitHub Actions: Run YouTube Shorts Pipeline (Free)

This file documents how to run the full YouTube Shorts pipeline using GitHub Actions (cron or manual).

Why use GitHub Actions
- Free tier offers 2 CPU cores + ~7GB RAM and ~14GB temp storage per runner.
- It can run MoviePy and perform video composition reliably for short videos.
- No persistent server required — the workflow renders the short and uploads it to YouTube.

What I added
- Workflow: `.github/workflows/generate_short.yml`
  - Triggers: scheduled (`cron`) and manual (`workflow_dispatch`).
  - Steps: checkout, setup Python, install ffmpeg, pip install requirements, run `python scripts/run_generate.py`.
  - Maps repository secrets into env vars for the process.

Required repository secrets
- `YOUTUBE_CLIENT_ID` — OAuth client id (if using refresh token flow)
- `YOUTUBE_CLIENT_SECRET` — OAuth client secret
- `YOUTUBE_REFRESH_TOKEN` — OAuth refresh token for channel upload
- `GROQ_API_KEY` — (optional) Groq API key if you use Groq
- `GROQ_API_URL` — (optional) Groq API URL if needed
- `TARGET_TOPIC` — (optional) topic for the run (defaults to `python`)
- `VIDEO_ASSEMBLY_TIMEOUT_SEC` — (optional) defaults to `600`

How to create a refresh token for YouTube (brief)
1. Create OAuth credentials in Google Cloud Console for an "Desktop" or "Web" app.
2. Locally run an interactive flow once (the repository supports `client_secrets.json`) or use a tool to obtain a refresh token.
3. Add the refresh token + client id/secret to GitHub repository secrets.

How to test locally before pushing secrets
1. Make sure `scripts/run_generate.py` works locally and uploads when your credentials are present.
2. Optionally set `STARTUP_VERIFICATION=false` in env to avoid the startup verifier running in the webserver (not relevant for Actions workflow).

Workflow tips & debugging
- If the workflow fails, check the Actions logs for step output and uploaded artifacts (`output/shorts/**` is captured on failure by the workflow configuration).
- For repeated runs that need increased runtime, set `VIDEO_ASSEMBLY_TIMEOUT_SEC` to a larger value in repo secrets or the workflow.
- If you hit LLM provider rate limits (Groq), you can:
  - Upgrade Groq plan
  - Switch to another LLM provider
  - Reduce generation frequency

Security considerations
- Keep `YOUTUBE_REFRESH_TOKEN` secret and scoped only to the specific channel account.
- Do not commit `client_secrets.json` or `credentials.json` into the repo.

Advanced options
- Use `actions/cache` to cache `~/.cache/pip` or other large assets to speed up runs.
- You can create a `workflow` that pushes the output video to cloud storage (S3 or GCS) before uploading, to keep artifacts.
- For long-running or memory-heavy workloads, consider using self-hosted runners or splitting the pipeline into multiple steps (generate assets, then render).

Example run (manual)
- Go to the repository > Actions > Generate and Upload a YouTube short > Run workflow > choose branch and run.


If you want, I can:
- Add artifact upload of the final video for safe retrieval.
- Add a separate job to run the minimal startup verification before the full job (so you can skip heavy work if auth fails).
- Provide exact GitHub UI steps for adding secrets — I can paste the copy-paste values for each secret name.
