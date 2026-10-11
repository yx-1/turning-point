# Development Notes

These notes are for the AIML 515 development report. Times are approximate for this working session.

## 2026-10-04 — New project, chat screen, and API health check

### Feature completed

- Created Turning Point as its own project, separate from PermitLens.
- Added a React + Vite chat screen with a welcome message, message bubbles, input validation, and a connection banner.
- Added a FastAPI `GET /health` endpoint.
- Connected the chat screen to that endpoint and confirmed the banner changes to `API connected: turning-point-api`.

Astrology, the conversation state machine, voice input, and SQLite are not built yet.

### Prompt / instruction used

First-task prompt: review the astrology chat specification, propose a simple local architecture, create the project structure, build the basic React chat interface, add FastAPI with `/health`, connect the two, run both, and stop before astrology or conversation logic. Organize it as a brand-new project. Do not use a paid LLM API in the running app.

### Problems encountered

- The open Cursor folder was the existing PermitLens app, so the new app could not be added at that repository root.
- `http://127.0.0.1:5173` did not open at first. Vite had bound only to `localhost`.
- `uvicorn --reload` watched the Python virtual environment and kept restarting while those files were touched.
- On a short screen, the message area could push the send box below the visible page.
- The frontend linter warned about updating React state at the start of the health-check effect.

### How they were fixed

- Created a new git repository at `/Users/yuxuanli/Documents/GitHub/turning-point` and continued work there.
- Set the Vite dev server host to `127.0.0.1` and documented that address.
- Started the API with `--reload-dir app`, so only application code triggers a reload.
- Made the chat shell fill the screen height and scroll only the message list, which keeps the send box on screen.
- The first health check now updates state after the request finishes. The Retry button still shows the checking state, because that update comes from a click.

### Architecture decisions

- Two local processes: React on port 5173 and FastAPI on port 8000.
- The browser calls `GET /health` directly. CORS allows the Vite origin. A dev proxy was not used, so the request path stays easy to see.
- The running app will not call an LLM. Later conversation steps will use a Python state machine and template text.
- SQLite will be a file created by the API. Planned path: `backend/turning_point.db`. It does not exist yet.
- Personal data stays on this computer. No paid AI, speech, geocoding, or astrology API is part of the design.

### Approximate development time

About 30 minutes.

## 2026-10-04 — Conversation state machine

### Feature completed

- The chat now collects a birth date, birth time, birth city, current city, and three life events, one question at a time.
- If an event sentence already contains a clear date, the date question is skipped.
- Missing or ambiguous answers get a follow-up instead of a guess.
- Life events are labeled with keyword categories such as career, relocation, education, and loss.
- The user can confirm the summary or start over. A Restart button clears the session.
- Astrology is still not calculated.

### Prompt / instruction used

Implement the local conversational state machine for birth details and three life events. Keep it deterministic, with no external AI API. Extract a date from an event sentence when it is clear. Ask a follow-up when it is not. Add Restart. Test the conversation through confirmation. Explain how state moves between React and FastAPI.

### Important files

- `backend/app/services/conversation_service.py` — session memory and the question order
- `backend/app/utils/parsing.py` — dates, times, cities, and keyword categories
- `backend/app/routes/conversation.py` — `POST /conversation/start`, `/message`, and `/restart`
- `backend/app/schemas/conversation.py` — JSON shapes
- `backend/tests/test_conversation.py` — state-machine checks
- `frontend/src/pages/ChatPage.tsx` — sends each answer and shows the replies
- `frontend/src/services/api.ts` — the three conversation requests
- `frontend/src/components/ChatWindow.tsx` — Restart button

### Problems encountered

- The word "may" in "I may have changed jobs in 2019" looked like the month May.
- The keyword "career" did not match the plural "careers".
- A numeric date such as 05/06/1997 can mean two different days.
- Reloading the API clears in-memory sessions, so an old session id stops working.

### How they were fixed

- "May" counts as a month only when it is part of a date, such as "May 8, 1997", or when the whole answer is "May".
- Added the plural keyword.
- Ambiguous numeric dates stay on the same question and ask for a month name.
- A missing session returns a clear message. Restart creates a new session.

### Architecture decision

Conversation state lives in a Python dictionary inside the API process, not in the browser and not in SQLite yet. The browser only stores the session id and the messages it displays. Each answer is judged by the backend.

### Approximate development time

About 90 minutes.

## 2026-10-04 — SQLite profile storage

### Feature completed

- The API creates `backend/turning_point.db` on startup.
- Saying yes at confirmation inserts one `UserProfile` and three `LifeEvent` rows.
- The response includes `user_id`. Saying yes again does not insert a second copy.
- Restart clears the in-memory chat and leaves saved rows alone.
- `GET /users/{user_id}` returns the profile and its events.
- A confirmed profile was still readable after Restart and after stopping and starting the API.

Astrology is still not calculated.

### Prompt / instruction used

Add SQLite persistence with SQLAlchemy. Keep the in-memory session for the active chat. On confirmation, save one profile and exactly three life events, return the user id, and do not save twice. Restart must not delete database rows. Add `GET /users/{user_id}`. Test that the row survives a frontend restart and a backend restart.

### Database setup

- Engine and table creation: `backend/app/database.py`
- Models: `backend/app/models/profile.py`
- `UserProfile`: id, birth_date, birth_time, birth_city, current_city, created_at
- `LifeEvent`: id, user_id, event_type, event_date, description, created_at
- File: `backend/turning_point.db`
- The file is ignored by git.

### Files changed

- `backend/app/database.py`
- `backend/app/models/profile.py`
- `backend/app/services/profile_service.py`
- `backend/app/services/conversation_service.py`
- `backend/app/routes/users.py`
- `backend/app/routes/conversation.py`
- `backend/app/schemas/conversation.py`
- `backend/app/schemas/user.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/tests/test_conversation.py`
- `frontend/src/services/api.ts`
- `frontend/src/components/ChatWindow.tsx`
- `.gitignore`
- `README.md`

### Problems encountered

- Unit tests would have written into the real database if they used the same file as the API.
- The first live confirmation had to be checked again after the API process was stopped, because an in-memory session would have disappeared.

### How they were fixed

- Tests set `TURNING_POINT_DB` to a temporary file and close that connection before the file is deleted.
- The live check called `GET /users/1` after Restart and again after a full API restart. The same three events were still there.

### Architecture decision

The chat session stays in a Python dictionary until confirmation. Only the structured profile is written to SQLite. Approximate dates such as "August 2019" and "2018" are stored as text, because they are not all full calendar days.

### Approximate development time

About 45 minutes.

## 2026-10-04 — Local chart, pattern comparison, future window, and reading

### Feature completed

- Added a local natal chart and major-transit check with Kerykeion.
- Compared the three saved life events and scored repeated patterns.
- Searched the next 18 months and returned one future window.
- Filled the reading with Python templates.
- Added an Analyze button, a loading state, the result view, and Start Over.

### Packages added

- `kerykeion==6.0.4` in `backend/requirements.txt`. It uses the local `libephemeris` package. It does not use pyswisseph, and the chart call sets `online=False` so it does not call GeoNames.

### Astrology logic

- Birth city coordinates come from `backend/app/data/cities.py`, a fixed list of major cities.
- The chart uses the saved birth date and time. An unknown time uses noon, and the Moon and Ascendant are left out of the aspect check.
- Transit planets are Jupiter, Saturn, Uranus, and Pluto.
- Aspects are conjunction, opposition, and square, within 7 degrees.
- Natal targets are the Sun, Moon, Mercury, Venus, Mars, Jupiter, and Saturn.
- A month-only event date uses the 15th. A season uses the middle month of that season. A year-only date uses July 1.

### Pattern scoring

- A pattern is one transit planet, one aspect, and one natal planet, such as "Pluto square natal Saturn".
- It counts only when it appears in at least two of the three events.
- Score = (number of events) × 10 + a tightness bonus from how close each hit is to exact.
- If nothing repeats, the reading uses the single tightest hit and says the events did not share a pattern.

### Future-search approach

- The search starts on the current date and steps forward 14 days for about 18 months.
- An exact repeat of the strongest past pattern ranks first.
- If that pair never comes within 7 degrees, the search keeps the tightest major aspect from the same planet.
- The window is the short cluster around the tightest sample, not every month where a slow planet is still inside a wide orb.
- The reading names one window.

### Prompt / instruction used

Implement the remaining MVP in one pass: local astrology calculation, past-event pattern comparison, one future transition window, and a template reading page. Use the saved profile and three life events. Do not call a paid API or an LLM. Show Analyze, a loading state, the reading, and Start Over. Test the full path and document limitations.

### Problems encountered

- Kerykeion 6 does not install `pyswisseph`. An import check for `swisseph` failed even though the library itself installed.
- Calculating every default chart point produced a warning about a body that is unavailable in sealed mode.
- Passing a city name into Kerykeion would have used an online geocoder.
- The first future-window version invented a calendar span when the exact past pattern did not return. For the saved Seattle profile, Pluto square natal Saturn does not recur in the next 18 months, so the page showed April–May 2027 while the explanation said it was not a real match.

### How they were fixed

- The chart uses Kerykeion's offline `from_birth_data` path with latitude, longitude, and a time zone. `swisseph` is not imported.
- `active_points` is limited to the ten planets used by this prototype.
- City names are resolved with the built-in list. An unknown city returns a 400 error instead of calling a geocoding API.
- The future search now falls back to the tightest similar aspect from the same planet, and the reading says when that is not an exact repeat. The Seattle profile's window is the tightest upcoming Pluto square, October–December 2026, and the text says the older Pluto-Saturn square does not return in this search.

### Architecture decisions

- `POST /users/{user_id}/reading` loads the SQLite rows, calculates the chart, and returns the reading. The reading is not stored.
- The wording is template text. It uses phrases such as "This period may be associated with" and includes the entertainment disclaimer.
- The result view is added under the confirmed chat. Start Over uses the existing restart path and clears the reading on screen.

### Files changed

- `backend/app/data/cities.py`
- `backend/app/services/astrology_service.py`
- `backend/app/services/pattern_service.py`
- `backend/app/services/reading_service.py`
- `backend/app/routes/readings.py`
- `backend/app/schemas/reading.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/tests/test_reading.py`
- `frontend/src/components/ReadingView.tsx`
- `frontend/src/pages/ChatPage.tsx`
- `frontend/src/services/api.ts`
- `README.md`

### Approximate development time

About 2 hours.
