# Environment

Use `.env.example` as the committed template for local configuration.

Rules:

- Commit `.env.example` and `.env.template` when they contain no secrets.
- Never commit `.env`, `.env.*`, private keys, credentials, or service account files.
- Add new environment variables to `.env.example` with blank or safe development values.

Current stacks: node, python, vue3-vite

The root `.env.example` mirrors the backend `Settings` fields in `backend/core/config.py`. The frontend currently uses Vite dev proxy settings from `frontend/vite.config.ts`; no active `VITE_*` variable is required by source code at this stage.
