#!/bin/sh
# Bootstrap an Ubuntu backend host for BTX Start.

set -eu
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

APP_USER="${APP_USER:-btxstart}"
APP_DIR="${APP_DIR:-/opt/btx-start}"
DATA_DIR="${DATA_DIR:-/var/lib/btx-start}"
ENV_FILE="${ENV_FILE:-/etc/btx-start/backend.env}"
REPO_URL="${REPO_URL:-https://github.com/pythonoptic-sketch/minebtx-start.git}"
FALLBACK_REPO_URL="${FALLBACK_REPO_URL:-https://github.com/pythonoptic-sketch/minebtx-start.git}"

err() { echo "error: $*" >&2; exit 1; }
log() { echo "[bootstrap] $*"; }

[ "$(id -u)" = "0" ] || err "run as root"
[ -f "$ENV_FILE" ] || err "$ENV_FILE missing; run deploy/scripts/generate-runtime-env.sh first"

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip git curl ca-certificates jq caddy

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

install -d -m 0755 "$APP_DIR"
install -d -m 0750 -o "$APP_USER" -g "$APP_USER" "$DATA_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  if ! git clone "$REPO_URL" "$APP_DIR"; then
    log "primary repo unavailable; cloning fallback repo"
    git clone "$FALLBACK_REPO_URL" "$APP_DIR"
  fi
else
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" reset --hard origin/main
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -e "$APP_DIR[backend]"

install -m 0644 "$APP_DIR/deploy/systemd/btx-start-api.service" /etc/systemd/system/btx-start-api.service
install -m 0644 "$APP_DIR/deploy/systemd/btx-start-stratum.service" /etc/systemd/system/btx-start-stratum.service
install -m 0644 "$APP_DIR/deploy/systemd/btx-start-payouts.service" /etc/systemd/system/btx-start-payouts.service
install -m 0644 "$APP_DIR/deploy/systemd/btx-start-payouts.timer" /etc/systemd/system/btx-start-payouts.timer
install -m 0644 "$APP_DIR/deploy/systemd/btx-start-network-agent.service" /etc/systemd/system/btx-start-network-agent.service
install -m 0644 "$APP_DIR/deploy/caddy/Caddyfile" /etc/caddy/Caddyfile

systemctl daemon-reload
systemctl enable caddy btx-start-api btx-start-stratum btx-start-network-agent btx-start-payouts.timer
systemctl restart caddy btx-start-api btx-start-stratum btx-start-network-agent
systemctl start btx-start-payouts.timer

log "backend services installed"
log "check API: curl -fsS http://127.0.0.1:8000/health"
log "check stratum: nc -vz 127.0.0.1 3333"
log "check network agent: systemctl status btx-start-network-agent"
