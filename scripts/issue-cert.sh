#!/usr/bin/env bash
# issue-cert.sh — obtain the first Let's Encrypt certificate.
#
# Usage: bash scripts/issue-cert.sh <domain> <email>
#
# Run this once, before enabling the :443 server block in nginx/default.conf.
# It starts nginx in HTTP-only mode (for the ACME challenge), issues the
# cert, then leaves the cert in nginx/certs/live/<domain>/ for nginx to use.
set -euo pipefail

DOMAIN="${1:?usage: issue-cert.sh <domain> <email>}"
EMAIL="${2:?usage: issue-cert.sh <domain> <email>}"

CERTS_DIR="nginx/certs"
WWW_DIR="nginx/certbot-www"

mkdir -p "$CERTS_DIR" "$WWW_DIR"

echo "[cert] issuing certificate for $DOMAIN"

# 1. Ensure nginx is up in HTTP-only mode (the ACME challenge location is
#    already served by nginx/default.conf at /.well-known/acme-challenge/).
echo "[cert] ensure nginx is up"
docker compose -f docker-compose.prod.yml up -d --no-deps nginx

# 2. Issue the cert via certbot in standalone-webroot mode.
echo "[cert] running certbot"
docker compose -f docker-compose.prod.yml -f docker-compose.tls.yml run --rm \
  certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "$EMAIL" \
  --agree-tos \
  --no-eff-email \
  -d "$DOMAIN"

# 3. Symlink the cert into nginx/certs/ (where nginx/default.conf expects them).
echo "[cert] symlinking cert into $CERTS_DIR/"
ln -sf "$CERTS_DIR/live/$DOMAIN/fullchain.pem" "$CERTS_DIR/fullchain.pem"
ln -sf "$CERTS_DIR/live/$DOMAIN/privkey.pem" "$CERTS_DIR/privkey.pem"

echo "[cert] enabling TLS server block"
mv -f nginx/tls.conf.disabled nginx/tls.conf 2>/dev/null || true

echo "[cert] done — TLS server block enabled, reload nginx"
echo "[cert] the renewal loop (docker-compose.tls.yml) will keep it fresh"
