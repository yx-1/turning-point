# Turning Point

Turning Point is a local conversational astrology prototype for a graduate course. The finished app will collect birth details and three major life events in a chat, compare past transits with a short future window, and show one reflective transition reading.

The chat collects birth details and three life events with a local state machine. Saying yes saves the profile to SQLite. Analyze then builds one local chart reading from that saved profile.

The running app does not call a paid AI API. Cursor is used only as a coding assistant.

## Architecture

Two local processes talk over HTTP:

```text
Browser (React, Vite, port 5173)
        |
        |  GET  /health
        |  POST /conversation/start
        |  POST /conversation/message
        |  POST /users/{user_id}/reading
        v
FastAPI (Python, port 8000)
        |
        |
        +--> In-memory session for the active chat
        |
        +--> SQLite file after the user confirms
             backend/turning_point.db
        |
        +--> Local ephemeris (Kerykeion) for the reading
```

The active chat is a guided state machine, not an open-ended language model. Confirmation writes one profile and three life events. Analyze loads those rows, calculates a small natal chart and major transits on this computer, and fills a fixed reading template. Restart clears the chat session and leaves saved rows in the database.

## Project layout

```text
turning-point/
  frontend/                 React + Vite chat interface
    src/
      components/           Chat layout, messages, and input
      pages/                Chat page state
      services/             Calls to the FastAPI backend
      types/                Shared TypeScript types
      styles/               Application CSS
  backend/
    app/
      main.py               FastAPI app, CORS, and database startup
      database.py           Opens backend/turning_point.db
      routes/               Conversation, profile, and reading routes
      models/               UserProfile and LifeEvent tables
      schemas/              Request and response models
      services/             Conversation, profile, astrology, pattern, and reading services
      data/                 Built-in city coordinates
      utils/                parsing.py reads dates, times, cities, and event keywords
    requirements.txt
  README.md
  DEVELOPMENT_NOTES.md
```

SQLite is created automatically at `backend/turning_point.db` the first time the API starts. That file is listed in `.gitignore`.

## Requirements

- Node.js 20 or newer
- npm
- Python 3.14 (the version used while building this slice)

## Run locally

Use two terminals.

Terminal 1, API:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app --port 8000
```

If `.venv` already exists, activate it and start `uvicorn`. The virtual environment in this folder was created during the first setup.

Terminal 2, chat interface:

```bash
cd frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Use that address, not `localhost`, so the page and the API share the same style of local URL.

The header should say `API connected: turning-point-api`. The assistant then asks for your birth date. Answer one question at a time. After you confirm, the reply includes a user id. Check that id with:

```bash
curl http://127.0.0.1:8000/users/1
```

Restart clears the chat. It does not delete saved profiles.

After the assistant says the profile was saved, click Analyze. The reading is calculated with Kerykeion on this computer. You can also request it directly:

```bash
curl -X POST http://127.0.0.1:8000/users/1/reading
```

Birth cities must be in the built-in list in `backend/app/data/cities.py`. That list is a testing set of major cities, not a world gazetteer. Month-only and year-only event dates are turned into one representative day before the transit check.

Optional API base URL: copy `frontend/.env.example` to `frontend/.env` if the API is not on `http://127.0.0.1:8000`.

## Check the API directly

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","service":"turning-point-api"}
```

## Privacy

This prototype keeps personal data on the local machine. Do not add an external AI or paid astrology API. The active conversation stays in memory. A confirmed profile and its three events are written to `backend/turning_point.db`.

## Not included yet

- Voice input
- A readings table. Each analysis is calculated when Analyze is clicked and is not stored.
