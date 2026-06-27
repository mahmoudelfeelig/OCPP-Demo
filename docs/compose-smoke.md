# Compose Smoke Check

Use this sequence to verify the scaffold locally:

1. Copy environment templates:
   - `cp .env.example .env`
   - `cp deploy/.env.example deploy/.env`
2. Build and start the stack:
   - `docker compose up --build`
3. Confirm the edge proxy:
   - `curl http://localhost:8080/healthz`
4. Confirm the backend:
   - `curl http://localhost:8080/api/health`
5. Open the UI:
   - `http://localhost:8080`

If the stack does not start, inspect `docker compose logs -f` and verify the `.env` files are present.
