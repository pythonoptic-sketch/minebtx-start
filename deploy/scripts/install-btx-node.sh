#!/bin/sh
# Install btxd/btx-cli and configure a private RPC node.
#
# This script does not download from an unverified URL by default. Provide
# either:
#   BTX_NODE_TARBALL=/path/to/btx-daemon.tar.gz
# or:
#   BTX_NODE_TARBALL_URL=https://trusted.example/btx-daemon.tar.gz
#   BTX_NODE_TARBALL_SHA256=<expected sha256>

set -eu
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

BTX_USER="${BTX_USER:-btx}"
CONF_DIR="${CONF_DIR:-/etc/btx}"
DATA_DIR="${DATA_DIR:-/var/lib/btx}"
ENV_FILE="${ENV_FILE:-/etc/btx-start/backend.env}"

err() { echo "error: $*" >&2; exit 1; }
log() { echo "[btx-node] $*"; }

[ "$(id -u)" = "0" ] || err "run as root"

if ! id "$BTX_USER" >/dev/null 2>&1; then
  useradd --system --home "$DATA_DIR" --shell /usr/sbin/nologin "$BTX_USER"
fi

install -d -m 0750 -o "$BTX_USER" -g "$BTX_USER" "$DATA_DIR"
install -d -m 0750 "$CONF_DIR"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ -n "${BTX_NODE_TARBALL:-}" ]; then
  cp "$BTX_NODE_TARBALL" "$TMP_DIR/btx-daemon.tar.gz"
elif [ -n "${BTX_NODE_TARBALL_URL:-}" ]; then
  [ -n "${BTX_NODE_TARBALL_SHA256:-}" ] || err "BTX_NODE_TARBALL_SHA256 is required with URL installs"
  curl -fsSL "$BTX_NODE_TARBALL_URL" -o "$TMP_DIR/btx-daemon.tar.gz"
else
  err "provide BTX_NODE_TARBALL or BTX_NODE_TARBALL_URL"
fi

if [ -n "${BTX_NODE_TARBALL_SHA256:-}" ]; then
  actual="$(sha256sum "$TMP_DIR/btx-daemon.tar.gz" | awk '{print $1}')"
  [ "$actual" = "$BTX_NODE_TARBALL_SHA256" ] || err "tarball sha256 mismatch: $actual"
fi

tar xzf "$TMP_DIR/btx-daemon.tar.gz" -C "$TMP_DIR"
find "$TMP_DIR" -type f -name btxd -exec install -m 0755 {} /usr/local/bin/btxd \;
find "$TMP_DIR" -type f -name btx-cli -exec install -m 0755 {} /usr/local/bin/btx-cli \;
[ -x /usr/local/bin/btxd ] || err "btxd not found in tarball"
[ -x /usr/local/bin/btx-cli ] || err "btx-cli not found in tarball"

[ -f "$ENV_FILE" ] || err "$ENV_FILE missing; run generate-runtime-env.sh first"
RPC_USER="$(sed -n 's/^BTX_RPC_USER=//p' "$ENV_FILE" | tail -1)"
RPC_PASS="$(sed -n 's/^BTX_RPC_PASSWORD=//p' "$ENV_FILE" | tail -1)"
[ -n "$RPC_USER" ] || err "BTX_RPC_USER missing from $ENV_FILE"
[ -n "$RPC_PASS" ] || err "BTX_RPC_PASSWORD missing from $ENV_FILE"

umask 077
cat > "$CONF_DIR/btx.conf" <<EOF
server=1
daemon=0
listen=1
rpcbind=127.0.0.1
rpcallowip=127.0.0.1
rpcuser=${RPC_USER}
rpcpassword=${RPC_PASS}
datadir=${DATA_DIR}
EOF
chown root:"$BTX_USER" "$CONF_DIR/btx.conf"
chmod 0640 "$CONF_DIR/btx.conf"

install -m 0644 deploy/systemd/btxd.service /etc/systemd/system/btxd.service
systemctl daemon-reload
systemctl enable --now btxd

log "btxd installed and started"
log "sync status: /usr/local/bin/btx-cli -conf=$CONF_DIR/btx.conf getblockchaininfo"
