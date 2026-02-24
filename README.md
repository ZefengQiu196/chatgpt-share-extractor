# ChatGPT Share Extractor Frontend

Static frontend for extracting ChatGPT share conversations into spreadsheets.

## Files

- `index.html`: full UI + extraction logic (no build step).
-  `scripts/local_chat_share_proxy.py`: local Python proxy for `/fetch` during local testing.
- `README.md`: step-by-step Worker setup guide.

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

## Local Proxy Script (`scripts/local_chat_share_proxy.py`)

Purpose:
1. Provides local CORS-safe proxy endpoint for the frontend.
2. Restricts target URLs to `https://chatgpt.com/share/...`.
3. Supports local origin allowlist and basic retries.

Endpoints:
1. `GET /health` -> returns `{"ok": true}`
2. `GET /fetch?url=<encoded_chatgpt_share_url>` -> returns fetched HTML

Common options:
1. `--host` (default `127.0.0.1`)
2. `--port` (default `8787`)
3. `--allowed-origins` (comma-separated, default includes `localhost/127.0.0.1` on ports `5500`, `5501`, `8000`)
4. `--timeout` (default `35`)
5. `--retries` (default `3`)
   
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


## Proxy Setup

For local testing, pages served on `localhost` still use local proxy (`http://127.0.0.1:8787`) automatically.

## Frontend Screenshot
<img width="1904" height="948" alt="image" src="https://github.com/user-attachments/assets/23055b30-eb1a-4d64-a84c-3c74f09c1d1b" />


