# Compose Smoke Transcript

This transcript was refreshed after Docker Desktop WSL integration was enabled for the `Ubuntu` distro.

# Intended Commands

```bash
docker compose build
docker compose up -d
./scripts/compose-smoke.sh
docker compose ps
docker compose logs --tail=80 backend
docker compose logs --tail=80 worker
```

# Expected Results

- `postgres`, `redis`, `backend`, `worker`, `frontend`, `simulator`, `caddy`, and `otel-collector` start.
- `http://localhost:8080/healthz` returns `ok`.
- `http://localhost:8080/api/health` returns `{"status":"ok"}`.
- `http://localhost:8080/api/ready` returns `{"status":"ready"}` after migrations complete.
- `http://localhost:8080` renders the operations UI.
- Backend logs are JSON structured.
- Worker logs show `worker_started`.

# Actual Transcript

Validated locally on 2026-06-26 with Docker Desktop WSL integration enabled.

```text
$ docker compose build
backend   Built
worker    Built
simulator Built
frontend  Built

$ docker compose up -d
postgres        Running / healthy
redis           Running / healthy
otel-collector  Running
backend         Running / healthy
worker          Running
frontend        Running / healthy
simulator       Running / healthy
caddy           Running / healthy

$ ./scripts/compose-smoke.sh
compose smoke check passed

$ docker compose exec caddy wget -qO- http://localhost:8080/healthz
ok

$ docker compose exec caddy wget -qO- http://localhost:8080/api/health
{"status":"ok"}
```

Final service status:

```text
ocpp-backend-demo-backend-1          Up (healthy)  0.0.0.0:8000->8000/tcp
ocpp-backend-demo-caddy-1            Up (healthy)  0.0.0.0:8080->8080/tcp
ocpp-backend-demo-frontend-1         Up (healthy)  0.0.0.0:3000->3000/tcp
ocpp-backend-demo-otel-collector-1   Up            0.0.0.0:4317-4318->4317-4318/tcp
ocpp-backend-demo-postgres-1         Up (healthy)  0.0.0.0:5432->5432/tcp
ocpp-backend-demo-redis-1            Up (healthy)  0.0.0.0:6379->6379/tcp
ocpp-backend-demo-simulator-1        Up (healthy)  0.0.0.0:9000->9000/tcp
ocpp-backend-demo-worker-1           Up            8000/tcp
```
