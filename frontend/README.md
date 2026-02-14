# Frontend (Vite + React)

This folder contains the frontend for the B2B chat demo built with React and Vite.

**This README explains how to run the frontend locally, how it talks to the Python backend, and basic troubleshooting steps.**

**Prerequisites:**
- Node.js (recommended v18+), `npm` (or `pnpm`/`yarn`) installed.
- Python 3.8+ and `pip` to run the local backend (optional if using a remote API).

**Ports used by default:**
- Frontend dev server: `5173` (Vite)
- Backend (Flask): `5000`

**Quick Start — Development**

1. Start the backend (required for the chat to work):

```bash
# from the repository root
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python backend/server.py
```

The local Flask server listens on `http://127.0.0.1:5000` and exposes a `/chat` POST endpoint. CORS is enabled in `backend/server.py` so the Vite dev server can talk to it.

2. Install frontend deps and run the dev server:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser to see the app.

**Build / Preview (production-like)**

```bash
cd frontend
npm run build
npm run preview
```

`npm run build` writes static files to `frontend/dist`. `npm run preview` serves the built files locally for a quick check.

**Configuration / Environment**

- The frontend currently uses a hard-coded backend URL in `frontend/src/ChatWidget.jsx`:

```js
fetch('http://127.0.0.1:5000/chat', { ... })
```

If you'd prefer to use an environment variable instead (recommended), add a `.env` file in `frontend/` with:

```
VITE_BACKEND_URL=http://127.0.0.1:5000
```

Then update the fetch call to use Vite's env variable:

```js
fetch(`${import.meta.env.VITE_BACKEND_URL}/chat`, { ... })
```

Changes to `.env` require restarting the Vite dev server.

**Useful npm scripts** (from `frontend/package.json`)
- `npm run dev` : start Vite dev server
- `npm run build`: build production bundle
- `npm run preview`: locally serve the production build
- `npm run lint` : run ESLint

**Files of interest**
- `frontend/src/ChatWidget.jsx` — chat UI and the fetch call to the backend
- `frontend/src/App.jsx` and `frontend/main.jsx` — app entry points
- `backend/server.py` — local Flask endpoint used in development

**Troubleshooting**
- Backend not reachable: ensure the Python backend is running and that you activated the virtualenv and installed `backend/requirements.txt`.
- CORS errors: `backend/server.py` enables CORS by default; verify the Flask server logs and that the request origin matches.
- Port conflicts: if `5173` or `5000` are in use, stop the occupying process or change the port (Vite accepts `--port` and Flask's `app.run(port=...)`).
- If the UI shows "Error: Backend not reachable.": check the browser console and network tab to see the request and response.
