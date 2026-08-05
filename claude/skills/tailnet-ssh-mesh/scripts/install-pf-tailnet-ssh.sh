#!/bin/bash
# Restrict inbound TCP/22 to the Tailscale tailnet only.
#
# Why this exists: macOS sshd is launchd socket-activated, so `ListenAddress`
# in sshd_config is silently ignored — sshd always listens on 0.0.0.0 and ::.
# pf is the only way to bind SSH to the tailnet in practice.
#
# Rollback:
#   sudo pfctl -d
#   sudo launchctl bootout system /Library/LaunchDaemons/com.tailnet-ssh.pf.plist
#   sudo rm /Library/LaunchDaemons/com.tailnet-ssh.pf.plist /etc/pf.anchors/com.tailnet-ssh
#   (and drop the two com.tailnet-ssh lines from /etc/pf.conf — a .bak is saved)

set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "ERROR: run this with sudo"; exit 1; }

ANCHOR=/etc/pf.anchors/com.tailnet-ssh
PLIST=/Library/LaunchDaemons/com.tailnet-ssh.pf.plist

echo "==> Writing $ANCHOR"
cat > "$ANCHOR" <<'RULES'
# Inbound SSH permitted ONLY from the Tailscale tailnet.
#   100.64.0.0/10        Tailscale CGNAT IPv4 range
#   fd7a:115c:a1e0::/48  Tailscale ULA IPv6 range
tailnet4 = "100.64.0.0/10"
tailnet6 = "fd7a:115c:a1e0::/48"

pass  in quick on lo0 proto tcp to port 22
pass  in quick inet   proto tcp from $tailnet4 to any port 22
pass  in quick inet6  proto tcp from $tailnet6 to any port 22
block drop in quick   proto tcp to any port 22
RULES
chmod 644 "$ANCHOR"

echo "==> Wiring anchor into /etc/pf.conf"
if ! grep -q 'com.tailnet-ssh' /etc/pf.conf; then
  cp /etc/pf.conf "/etc/pf.conf.bak.$(date +%Y%m%d%H%M%S)"
  printf '\nanchor "com.tailnet-ssh"\nload anchor "com.tailnet-ssh" from "%s"\n' "$ANCHOR" >> /etc/pf.conf
  echo "    added (backup saved)"
else
  echo "    already present"
fi

echo "==> Validating ruleset (no load)"
if ! pfctl -n -f /etc/pf.conf; then
  echo "ERROR: ruleset failed validation — nothing was enabled."
  exit 1
fi

echo "==> Installing boot-persistence LaunchDaemon"
cat > "$PLIST" <<'PL'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.tailnet-ssh.pf</string>
  <key>ProgramArguments</key>
  <array>
    <string>/sbin/pfctl</string>
    <string>-E</string>
    <string>-f</string>
    <string>/etc/pf.conf</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><false/>
</dict>
</plist>
PL
chmod 644 "$PLIST"
chown root:wheel "$PLIST"
launchctl bootout   system "$PLIST" 2>/dev/null || true
launchctl bootstrap system "$PLIST" 2>/dev/null || true

echo "==> Enabling pf now"
pfctl -E -f /etc/pf.conf 2>&1 | grep -Ei 'enabled|token|error' || true

echo
echo "==> Rules loaded from $ANCHOR:"
grep -E '^(pass|block)' "$ANCHOR" | sed 's/^/    /'
echo
echo "==> Kernel anchor listing (NOTE: Apple's pfctl under-reports here —"
echo "    it may show only the first rule even when all are active."
echo "    Trust the behavioural test, not this output):"
pfctl -a com.tailnet-ssh -s rules 2>/dev/null | sed 's/^/    /'
echo
echo "==> pf status: $(pfctl -s info 2>/dev/null | head -1)"
echo
echo "VERIFY from another machine on the same LAN:"
echo "    nc -G 6 -z <this-mac-LAN-ip> 22   # should HANG then fail = blocked"
echo "    nc -G 6 -z <this-mac-100.x-ip> 22 # should succeed = tailnet OK"
echo "DONE"
