# Hetzner Deployment

This project is designed to run on a single Hetzner VM with Docker Compose and Caddy.
The recommended setup is:

- host-level Caddy terminates TLS for all projects on the box
- each project runs its own Docker Compose stack
- each public-facing app edge container joins the shared external Docker network `web`
- host Caddy routes `ocpp.elfeel.me` to the app edge container `ocpp-demo-edge:8080`

## Prerequisites

- Ubuntu server on Hetzner
- Docker Engine and the Compose plugin installed
- Caddy installed on the host if you want one reverse proxy for multiple projects
- a GitHub container registry token with read access to the repository images

## Server Layout

Suggested paths:

- `/srv/ocpp-backend-demo` for this repository checkout
- `/srv/projects/<other-project>` for sibling apps
- `/opt/ocpp-backend-demo` for this app
- `ocpp-demo-edge:8080` for this app's internal edge proxy on the `web` network
- one host Caddy site block per domain/subdomain

## Initial Setup

1. Clone the repository on the server:
   - `git clone <your-repo-url> /srv/ocpp-backend-demo`
2. Copy the production environment file:
   - `cp /srv/ocpp-backend-demo/deploy/.env.example /srv/ocpp-backend-demo/deploy/.env`
3. Fill in the production values in `deploy/.env`:
   - database password
   - JWT secret
   - partner webhook secret
   - `GHCR_OWNER`
   - any bootstrap admin credentials
4. Set up host Caddy:
   - add a site block that reverse proxies `ocpp.elfeel.me` to `ocpp-demo-edge:8080`
5. Start the stack:
   - `cd /srv/ocpp-backend-demo`
   - `docker compose --env-file deploy/.env -f docker-compose.prod.yml up -d`

## Host Caddy Example

Use the snippet in [`deploy/Caddyfile.host.example`](/mnt/d/Stuff/Projects/Tools/OCPP-Demo/deploy/Caddyfile.host.example):

```caddy
ocpp.elfeel.me {
    reverse_proxy ocpp-demo-edge:8080
}
```

## Updating The Stack

When the GitHub Actions workflow publishes a new image:

1. SSH into the server or let the workflow do it for you.
2. Pull the new images:
   - `docker compose --env-file deploy/.env -f docker-compose.prod.yml pull`
3. Recreate the services:
   - `docker compose --env-file deploy/.env -f docker-compose.prod.yml up -d --remove-orphans`

## Secrets

- Keep `deploy/.env` on the server only.
- Do not commit the server file.
- Store the GHCR read token in GitHub Actions secrets.

## Notes

- This stack uses its own local Caddy container for path routing inside the app stack.
- Host Caddy sits in front of that container on the shared Docker network `web`, so other projects can coexist on the same server without publishing app ports.
- If you prefer to route directly from host Caddy to backend/frontend/simulator containers, remove the app Caddy service and publish the individual ports instead.
