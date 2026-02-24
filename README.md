# Chat Share Extractor Frontend

Static frontend for extracting ChatGPT share conversations into spreadsheets.

## Files

- `frontend/index.html`: full UI + extraction logic (no build step).
- `frontend/worker/cloudflare-worker.js`: proxy template for CORS-safe fetching.
- `frontend/worker/README.md`: step-by-step Worker setup guide.
- `index.html` (repo root): redirect entry for GitHub Pages root publish mode.

## Output Format

Each extracted conversation workbook uses this fixed 7-column schema:

1. `Round`
2. `Prompt`
3. `Prompt_upload`
4. `ChatGPT's thought time`
5. `ChatGPT's thought`
6. `ChatGPT's response`
7. `ChatGPT's response code`

Batch ZIP output always contains:

1. `results/<name>.xlsx` files
2. `status.xlsx` with strict columns: `Name.dot`, `Link`, `Status`, `Reason`, `Round_count`

## Local Run (No Deploy)

From repo root:

```powershell
python scripts/local_chat_share_proxy.py --host 127.0.0.1 --port 8787
```

In another terminal:

```powershell
python -m http.server 8000
```

Open: `http://localhost:8000/`

For VS Code Live Server, start `scripts/local_chat_share_proxy.py` first. The frontend detects `localhost` and uses `http://127.0.0.1:8787` as its proxy base automatically.

## GitHub Pages (Repository Root Mode)

1. Push this repo to GitHub.
2. In GitHub repo settings, open `Pages`.
3. Set source to `Deploy from a branch`.
4. Select branch `main` (or your default branch), folder `/ (root)`.
5. Save and wait for deployment.
6. Open your Pages URL. It will load the app via root `index.html` redirect to `frontend/index.html`.

## Proxy Setup

After Pages is live, deploy the Cloudflare Worker from `frontend/worker/cloudflare-worker.js`.

Then set the fixed proxy in `frontend/index.html`:

`const FIXED_PROXY_BASE = "https://chat-share-proxy.<subdomain>.workers.dev";`

For local testing, pages served on `localhost` still use local proxy (`http://127.0.0.1:8787`) automatically.
Then redeploy GitHub Pages. End users do not need to configure proxy settings in the UI.
