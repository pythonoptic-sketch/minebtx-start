#!/bin/sh
# Quick non-destructive check for the CPX31 backend host.

set -eu
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

failures=0

fail() {
  failures=$((failures + 1))
  printf '[fail] %s\n' "$*" >&2
}

pass() {
  printf '[pass] %s\n' "$*"
}

need() {
  if command -v "$1" >/dev/null 2>&1; then
    pass "found $1"
  else
    fail "missing $1"
  fi
}

need uname
need df
need free
need awk
need curl
need git
need systemctl

os="$(. /etc/os-release 2>/dev/null && printf '%s' "${PRETTY_NAME:-unknown}" || printf unknown)"
case "$os" in
  *"Ubuntu 24.04"*) pass "OS is $os" ;;
  *) fail "expected Ubuntu 24.04, found $os" ;;
esac

mem_mb="$(free -m | awk '/^Mem:/ {print $2}')"
if [ "${mem_mb:-0}" -ge 7000 ]; then
  pass "RAM looks sufficient: ${mem_mb} MB"
else
  fail "RAM below CPX31 target: ${mem_mb:-unknown} MB"
fi

root_gb="$(df -BG / | awk 'NR==2 {gsub(/G/, \"\", $2); print $2}')"
if [ "${root_gb:-0}" -ge 140 ]; then
  pass "root disk looks sufficient: ${root_gb} GB"
else
  fail "root disk below CPX31 target: ${root_gb:-unknown} GB"
fi

if systemctl is-system-running >/dev/null 2>&1 || systemctl is-system-running | grep -Eq 'running|degraded'; then
  pass "systemd is available"
else
  fail "systemd does not look healthy"
fi

if [ "$failures" -gt 0 ]; then
  printf '\nServer readiness check failed with %d issue(s).\n' "$failures" >&2
  exit 1
fi

printf '\nServer readiness check passed.\n'
