# Mem0 GrowthOS

Mem0 GrowthOS is a Flask dashboard for turning Mem0's developer pain-point pipeline into a simple internal growth tool.

The app scans for real AI memory pain points, groups them into signal cards, helps draft outreach, creates reusable content, and shows a short set of session insights. It is designed to feel like a small SaaS product the growth team could actually use, not a demo.

## What It Does

The workflow is intentionally simple:

1. Open the app and start on a quiet landing state.
2. Click `Scan Now`.
3. The backend runs the agent pipeline from `main.py`.
4. The dashboard fills with:
   - `Signal Radar`: discovered pain points
   - `Outreach Composer`: a plain-language message for one selected signal
   - `Content Command`: LinkedIn, blog hook, and intro email drafts
   - `Insights`: charts and short observations from the current scan
5. Save signals, edit drafts, regenerate content, and export the latest markdown output.

The UI stays static until a scan runs. After that, the session state lives in the browser and the backend keeps the latest export in `outputs.md`.

## Stack

- Backend: Flask in `app.py`
- Pipeline logic: `main.py`
- Frontend: single HTML file in `templates/index.html`
- Styling and behavior: vanilla CSS and JavaScript only
- Typography: Inter from Google Fonts
- LLM: Gemini via the Google SDK used in `main.py`

## Routes

- `GET /` serves the dashboard
- `POST /scan` runs the full pipeline and returns the full session as JSON
- `POST /run` is a compatibility alias for `/scan`
- `POST /compose` creates outreach drafts for one selected signal
- `POST /regenerate-content` rewrites the content assets, optionally with a focus angle
- `POST /insights` regenerates the strategic observations for the current session
- `GET /export` downloads `outputs.md`
- `GET /run-stream` is a compatibility SSE endpoint for older clients

## Project Files

- `main.py`: the agent pipeline and Gemini helper functions
- `app.py`: Flask app and session/export routes
- `templates/index.html`: the full dashboard UI
- `outputs.md`: latest generated session export
- `.env`: stores `GEMINI_API_KEY`

## Run Locally

1. Add your API key to `.env`:

```bash
GEMINI_API_KEY=your_key_here
```

2. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

Open the URL printed in the terminal. The app tries `http://localhost:5000` first and falls back to the next free port if needed.

## How the UI Works

- The left sidebar switches between the four modules.
- Signal cards are clickable and open the composer.
- Save state is remembered in the browser for the session.
- Draft text can be edited directly in the dashboard.
- Copy buttons copy the current message or content block to the clipboard.
- Charts in `Insights` are rendered with SVG and pure CSS styling.

## Notes

- `app.py` imports the pipeline functions from `main.py`, so the core logic stays in one place.
- The latest session is persisted to `outputs.md` whenever the scan or export path runs.
- The app has fallback paths so the dashboard can still render even if the Gemini call fails or quota is exhausted.
