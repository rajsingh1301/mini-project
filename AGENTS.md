# AGENTS.md

Instructions for coding agents (Codex etc.) working in this repository.
Project: "Guide Eye", real-time spoken guidance for visually impaired people (see README.md).

## Your area: `frontend/` only
You work on the React + Vite phone app in `frontend/` (`src/`, `styles.css`, `public/`, `package.json`).
Another agent works on the backend at the same time, in the same folder. To avoid conflicts:

1. **Only edit files inside `frontend/`.** Never edit `modules/`, `server.py`, `config.py`,
   `training/`, `tests/`, `main.py`, `README.md`, `CLAUDE.md`, `.gitignore` or `requirements.txt`.
2. **Commit only your folder:** `git add frontend/` then `git commit`. Never `git add -A` or
   `git add .` (that would commit the other agent's unfinished work). Never `git push --force`,
   `git reset --hard` or `git checkout .`/`git stash` (they touch files you do not own).
   If git says an `index.lock` exists, wait a few seconds and try again.
3. **The backend contract is `docs/api.md`.** Use only the fields listed there. Do not parse
   spoken text (arrows, colours and vibration come from `direction`, `alert`, `clear`).
   If you need a new field or a change, do not work around it: write down what you need
   (in your final message or in `frontend/NEEDS_BACKEND.md`) and the backend agent adds it.
4. Do not edit `docs/api.md`. It belongs to the backend.

## Frontend conventions
- React 18, plain JS (no TypeScript, no UI library). Hooks in `src/hooks/` own side effects;
  pure logic goes in `src/lib/` with `node --test` tests.
- Every visible or spoken app message lives in `src/lib/i18n.js` (English and Hindi). Add both
  languages for every new string: `npm test` fails if one is missing. Phrases about the
  surroundings and sign explanations come from the server already translated.
- Accessibility first: big touch targets, high contrast, everything important is also spoken,
  keep `aria-label`s translated.
- Browser speech is never queued: urgent phrases interrupt, ordinary ones are dropped while speaking.

## Commands (run inside `frontend/`)
```bash
npm install
npm test            # pure helper tests
npm run build       # writes frontend/dist, which the backend serves
npm run dev         # hot reload; needs the backend: `uvicorn server:app --port 8000` from the repo root
```
