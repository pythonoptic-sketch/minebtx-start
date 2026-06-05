#!/bin/sh
# Bootstrap an Ubuntu host for the Evarian travel app.

set -eu
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

APP_USER="${APP_USER:-evarian}"
APP_DIR="${APP_DIR:-/opt/evarian}"
DATA_DIR="${DATA_DIR:-/var/lib/evarian}"
REPO_URL="${REPO_URL:-https://github.com/pythonoptic-sketch/minebtx-start.git}"

err() { echo "error: $*" >&2; exit 1; }
log() { echo "[evarian-bootstrap] $*"; }

[ "$(id -u)" = "0" ] || err "run as root"

apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3 python3-venv python3-pip git curl ca-certificates caddy

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

install -d -m 0755 "$APP_DIR"
install -d -m 0750 -o "$APP_USER" -g "$APP_USER" "$DATA_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin main
  git -C "$APP_DIR" reset --hard origin/main
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -e "$APP_DIR[backend]"

install -m 0644 "$APP_DIR/deploy/systemd/evarian-api.service" /etc/systemd/system/evarian-api.service
install -m 0644 "$APP_DIR/deploy/caddy/Caddyfile" /etc/caddy/Caddyfile

systemctl daemon-reload
systemctl enable caddy evarian-api
systemctl restart evarian-api caddy

log "Evarian services installed"
log "check local API: curl -fsS http://127.0.0.1:8000/api/health"
log "check public site: curl -I https://drinknile.com/"
