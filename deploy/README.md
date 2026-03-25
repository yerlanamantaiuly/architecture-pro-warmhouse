# VPS Deployment Guide

This directory contains the production-oriented files for deploying the current WarmHouse stack to a VPS.

## Target topology

- `nginx` runs on the VPS host and terminates TLS.
- Docker Compose runs the application stack privately on the VPS.
- Only `80` and `443` should be exposed to the public internet.

## DNS

Create the following DNS records and point them to your VPS public IP:

- `A` record for the root domain, for example `example.com`
- `A` record for the subdomain, for example `warmhouse.example.com`

Choose one hostname as canonical. The sample `nginx` config assumes the subdomain is canonical and redirects the root domain to it.

For your current setup:

- `yerlan-amantaiuly.kz -> 94.131.86.166`
- `warmhouse.yerlan-amantaiuly.kz -> 94.131.86.166`
- optional: `www.yerlan-amantaiuly.kz -> 94.131.86.166`

## Files in this directory

- `nginx/warmhouse.conf.example` - sample host-level `nginx` server block
- `nginx/yerlan-amantaiuly.kz.conf` - ready-to-use config for your current domain choice
- `compose/docker-compose.prod.yml` - production Compose file that pulls images from GHCR
- `compose/.env.example` - server-side environment variables template
- `postgres/init.sql` - PostgreSQL bootstrap schema

## VPS preparation

1. Install Docker Engine and the Docker Compose plugin.
2. Install `nginx` and `certbot`.
3. Copy either:
   - `deploy/nginx/warmhouse.conf.example` and replace placeholders, or
   - `deploy/nginx/yerlan-amantaiuly.kz.conf` if you want to use the ready-made config for your domain
4. Place the file at `/etc/nginx/sites-available/warmhouse.conf`.
5. Enable the site and test the configuration:

```bash
sudo ln -s /etc/nginx/sites-available/warmhouse.conf /etc/nginx/sites-enabled/warmhouse.conf
sudo nginx -t
sudo systemctl reload nginx
```

## TLS certificates

After DNS is pointing to the VPS and `nginx` serves HTTP, request certificates:

```bash
sudo certbot --nginx -d __PRIMARY_DOMAIN__ -d __REDIRECT_DOMAIN__
```

For your chosen layout:

```bash
sudo certbot --nginx -d warmhouse.yerlan-amantaiuly.kz -d yerlan-amantaiuly.kz -d www.yerlan-amantaiuly.kz
```

Then verify automatic renewal:

```bash
sudo systemctl status certbot.timer
```

## Production Compose

Place the production files on the VPS, for example in `/opt/warmhouse`:

```text
/opt/warmhouse/
  compose/docker-compose.prod.yml
  compose/.env
  postgres/init.sql
```

Create `.env` from `.env.example`, then start the stack:

```bash
cd /opt/warmhouse/compose
docker compose --env-file .env up -d
```

Example `.env` for the VPS:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=strong-password
POSTGRES_DB=postgres
APP_DATABASE_NAME=smarthome
GHCR_OWNER=yerlanamantaiuly
IMAGE_TAG=latest
TEMPERATURE_DELAY_MS=0
TEMPERATURE_FAILURE_RATE=0
```

The sample production Compose maps the monolith to `127.0.0.1:8080` and keeps PostgreSQL and `temperature-api` internal-only, so `nginx` can proxy traffic to the monolith without exposing internal services.

## Required GitHub secrets

- `VPS_HOST`
- `VPS_PORT`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_APP_DIR`
- `GHCR_USERNAME`
- `GHCR_PULL_TOKEN`
- `APP_DOMAIN`
- `APP_REDIRECT_DOMAIN`

Use a GitHub PAT with `read:packages` for `GHCR_PULL_TOKEN` if the VPS needs explicit access to private GHCR packages.

For your setup, the domain-related secrets should be:

- `APP_DOMAIN=warmhouse.yerlan-amantaiuly.kz`
- `APP_REDIRECT_DOMAIN=yerlan-amantaiuly.kz`

After each deployment, the workflow runs `deploy/scripts/smoke-check.sh` against both the canonical domain and the redirecting domain.

## Recommended firewall

Allow only:

- `22/tcp`
- `80/tcp`
- `443/tcp`
