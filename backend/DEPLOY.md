# Deploying the backend

Docker Compose + a reverse proxy (Traefik) + a Cloudflare Tunnel, so nothing
needs a public IP or open ports. This is how the reference deployment
(`https://volvowatchapp.tallimedia.com`) runs; any similar host works.

## Layout on the host

```
~/volvowatch/
  Dockerfile  compose.yaml  pyproject.toml  app/  tests/  spike/
  .env          # PRODUCTION secrets, chmod 600, NOT in git
  data/         # sqlite db (bind-mounted to /app/data)
```

## First deploy

```bash
# from this repo's backend/ dir:
tar czf /tmp/backend.tgz --exclude=.venv --exclude=data --exclude=__pycache__ \
    --exclude=.env --exclude='spike/.refresh_token' .
ssh <your-host> 'mkdir -p ~/volvowatch/data'
cat /tmp/backend.tgz | ssh <your-host> 'tar xzf - -C ~/volvowatch'
# write ~/volvowatch/.env with production values (see .env.example), then:
ssh <your-host> 'cd ~/volvowatch && docker compose up -d --build'
ssh <your-host> 'wget -qO- http://localhost:8756/healthz'   # {"ok":true}
```

Production `.env` differences from local:
- `VOLVO_REDIRECT_URI=https://<your-public-hostname>/auth/callback`
- `PUBLIC_BASE_URL=https://<your-public-hostname>`
- `DATABASE_URL=sqlite:////app/data/volvowatch.db` (absolute, 4 slashes)
- fresh `FERNET_KEY` + `DEVICE_TOKEN_PEPPER` (independent of local dev)
- `FUEL_TANK_LITRES` set to your vehicle's actual tank size

## Redeploy after code changes

```bash
tar czf /tmp/backend.tgz --exclude=.venv --exclude=data --exclude=__pycache__ \
    --exclude=.env --exclude='spike/.refresh_token' .
cat /tmp/backend.tgz | ssh <your-host> 'tar xzf - -C ~/volvowatch'
ssh <your-host> 'cd ~/volvowatch && docker compose up -d --build'
```

**If your `compose.yaml` on the host has deployment-specific edits** (a custom
Docker network name, extra labels, etc.), exclude it from the tarball too —
`--exclude=compose.yaml` — so a redeploy doesn't clobber them.

The sqlite db in `~/volvowatch/data/` survives rebuilds (bind mount). Back it up
before schema changes: `ssh <your-host> 'cp ~/volvowatch/data/volvowatch.db{,.bak}'`.

**The container runs as uid 1000 (non-root)**, so the bind-mounted `data/` and
everything in it must be owned by 1000. If the db was ever written by a
root-running container, fix it once:

```bash
ssh <your-host> 'docker run --rm -v "$HOME/volvowatch/data:/d" alpine chown -R 1000:1000 /d'
```

Symptom of getting this wrong: reads work, writes silently fail (pairing,
token refresh).

## Routing (one-time, outside this repo)

The reference deployment uses Traefik's **file provider**, not Docker
auto-discovery — some Docker Engine versions ship an API newer than what
Traefik's bundled client hardcodes, which breaks auto-discovery outright. File
provider also means no Docker socket needs to be mounted into Traefik, which
is a smaller attack surface regardless.

1. **Traefik**: a static route file mapping your public hostname to
   `http://<host>:8756` (or wherever the container's port lands), `websecure`,
   TLS on, no middlewares needed (the app does its own auth).
2. **Cloudflare Tunnel**: add a public hostname pointing at Traefik, matching
   the same reverse-proxy chain. Auto-creates the DNS record if you're using
   Cloudflare for DNS too.
3. **Volvo app**: add the matching redirect URI,
   `https://<your-public-hostname>/auth/callback`, in the Volvo Cars
   Developer Portal.
