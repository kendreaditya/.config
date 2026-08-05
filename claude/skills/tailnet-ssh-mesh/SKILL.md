---
name: tailnet-ssh-mesh
description: Build an all-to-all SSH mesh across personal machines over Tailscale, then lock port 22 down to the tailnet. Covers which platforms can run a Tailscale SSH server vs. native OpenSSH, keyless key-distribution via a rendezvous host, sshd hardening drop-ins, pf (macOS) and ufw (Linux) rules that restrict SSH to the tailnet, and the verification gotchas that make these changes look broken when they are working. Use when setting up SSH between laptops/servers/phones on a tailnet, when "ssh <host>" times out on one machine but works on another, when hardening an exposed sshd, or when a firewall rule appears not to apply.
---

# Tailnet SSH mesh

Machine-specific values (hostnames, tailnet IPs, MagicDNS suffix, LAN
addresses, port inventories) are deliberately **not** in this file — this skill
lives in a public repo. Look for them in the operator's private notes
(`~/.claude/memory/`) or ask. Everything below is generic.

## 1. Decide what each node can actually run

Check this **before** planning, because two of these are hard blockers:

| Platform | Can run Tailscale SSH server? | Can run native OpenSSH? |
|---|---|---|
| Linux | Yes | Yes |
| macOS, open-source `tailscaled` CLI variant | Yes | Yes |
| macOS, **Mac App Store / standalone GUI** | **No** — sandboxed | Yes (Remote Login) |
| iOS / iPadOS | No | **No — there is no sshd at all** |

Consequences that reshape the plan:

- A **phone is client-only, permanently.** "All-to-all" across N devices
  including a phone is really a mesh of the N−1 non-phone devices. Say this
  out loud early rather than discovering it at verification time.
- On App Store Tailscale, macOS nodes **must** use native OpenSSH. Switching to
  the open-source `tailscaled` gets you Tailscale SSH (keyless, ACL-governed,
  tailnet-only) but costs the menubar GUI and needs re-auth. That is a real
  trade-off — surface it, don't pick silently.

Verify the variant rather than assuming:

```bash
tailscale version
ls /Applications/Tailscale.app/Contents/_MASReceipt   # exists => App Store build
tailscale debug prefs | grep RunSSH                   # true => TS SSH server on
```

## 2. Check the tailnet ACL before touching hosts

Nothing works if the tailnet packet filter drops :22. Inspect what the node
actually accepts — no admin console needed:

```bash
tailscale debug netmap | python3 -c "import sys,json;print(json.dumps(json.load(sys.stdin).get('PacketFilter'),indent=1)[:1200])"
```

A default-open tailnet shows the whole `100.64.0.0/10` CGNAT range with all
ports. If SSH is restricted, add `ssh` rules in the ACL policy first.

## 3. Distribute keys with a rendezvous host — no passwords

If any node already runs **Tailscale SSH**, it authenticates by tailnet
identity and needs no key. That makes it a perfect rendezvous: every other node
can reach it keylessly, so keys can be exchanged without typing a password
anywhere and without `ssh-copy-id`.

On each machine joining the mesh:

```bash
ssh <rendezvous> 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys \
  && chmod 600 ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys \
  && sort -u -o ~/.ssh/authorized_keys ~/.ssh/authorized_keys' < ~/.ssh/id_ed25519.pub
ssh <rendezvous> 'cat ~/.ssh/authorized_keys ~/.ssh/id_ed25519.pub' >> ~/.ssh/authorized_keys
sort -u -o ~/.ssh/authorized_keys ~/.ssh/authorized_keys
```

**This pattern is not idempotent across machines.** It pulls peer keys *once*,
so a node bootstrapped earlier never learns about one added later. Adding node
C leaves A→C working but C→A broken. Fix by relaying the new key through the
rendezvous, which can reach everyone:

```bash
cat ~/.ssh/id_ed25519.pub | ssh <rendezvous> 'ssh <stale-node> "cat >> ~/.ssh/authorized_keys"'
```

Always use **MagicDNS FQDNs** (`host.<tailnet>.ts.net`) in scripts, never bare
short names — see §7 for why.

## 4. Harden sshd

Drop-in file, since both macOS and Debian/Ubuntu `sshd_config` carry
`Include /etc/ssh/sshd_config.d/*`:

```
# /etc/ssh/sshd_config.d/010-tailnet-hardening.conf
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
AllowUsers <your-login>
MaxAuthTries 3
LoginGraceTime 20
```

Name it so it **sorts before** the vendor file (macOS ships `100-macos.conf`):
sshd takes the **first** value it sees for each keyword, so a later file cannot
override an earlier one. Validate with `sudo sshd -t` before relying on it.

`AllowUsers` will lock out every other account — check `ls /home` (or
`dscl . -list /Users`) first if the box is shared.

On macOS no restart is needed: sshd is launchd socket-activated, one process
per connection, so the next connection picks up the new config and existing
sessions are never dropped. On systemd: `sudo systemctl reload ssh`.

## 5. Restrict :22 to the tailnet

### macOS — pf (the only option)

macOS sshd is **socket-activated by launchd**, which owns the listening socket.
Therefore **`ListenAddress` in sshd_config is silently ignored** — sshd always
binds `0.0.0.0` and `::`, on every network the laptop joins. It also advertises
`_ssh._tcp` over Bonjour. pf is the only practical way to scope it.

`scripts/install-pf-tailnet-ssh.sh` in this skill installs an anchor passing
tcp/22 only from `100.64.0.0/10` and `fd7a:115c:a1e0::/48`, wires it into
`/etc/pf.conf` with a backup, validates before loading, and adds a LaunchDaemon
so it survives reboot.

Container runtimes (Colima, Docker Desktop) also drive pf and may already have
it enabled — and can flush custom rules. If the LAN port becomes reachable
again later, re-run `sudo pfctl -E -f /etc/pf.conf`.

### Linux — use the existing frontend, don't hand-write nftables

If `ufw` is active, **ufw already is the nftables frontend**; adding raw `nft`
rules alongside it gets clobbered. Check first:

```bash
sudo ufw status verbose        # note the ALLOW IN Anywhere entries, and their (v6) twins
```

Scope SSH to the tailnet by adding the narrow rules *before* removing the broad
one, so you are never briefly locked out:

```bash
sudo ufw allow from 100.64.0.0/10 to any port 22 proto tcp comment 'SSH tailnet v4'
sudo ufw allow from fd7a:115c:a1e0::/48 to any port 22 proto tcp comment 'SSH tailnet v6'
sudo ufw delete allow 22/tcp
```

Audit the **whole** table, not just SSH. `ALLOW IN Anywhere` rules for SMB,
VNC, RDP or web UIs are usually far more dangerous than sshd, and each one
typically has an IPv6 twin. A host with globally routable IPv6 is exposed to
the internet through those even when IPv4 sits behind NAT.

Tailscale SSH runs inside tailscaled's own netstack, so it keeps working
independently of ufw — handy as a fallback while editing firewall rules.

## 6. Verify behaviourally — the listings lie

Run these **from a different machine on the same LAN**, never from the host
itself: a host connecting to its own LAN address goes via loopback and matches
the `pass on lo0` rule, which looks like the block failed.

```bash
nc -G 6 -z <target-lan-ip>     22   # want: hang then fail  => blocked
nc -G 6 -z <target-tailnet-ip> 22   # want: succeed         => tailnet OK
```

- **`nc -w` does not bound the connect phase on macOS — use `-G`.** `block drop`
  discards silently rather than refusing, so connects hang. With `-w` alone the
  test looks like a broken command instead of a successful block.
- **`pfctl -a <anchor> -s rules` can under-report**, listing a subset while all
  rules are provably enforcing. Never disable a working ruleset because this
  listing looks short — trust the connection test.
- **`lsof -nP -iTCP:22 -sTCP:LISTEN` shows nothing for root-owned sockets when
  run unprivileged.** Use `netstat -an | grep LISTEN` to check sshd is up.
- Key-only auth reads as `Permission denied (publickey)`. If you still see
  `(publickey,password,keyboard-interactive)` the hardening did not take.
- Test with `-o BatchMode=yes` so a password fallback can't silently mask a
  broken key.

Beware shell redirection in nested test commands: `ssh A 'ssh B "echo x->y ok"'`
makes `>` a redirect on the far side, creating a file and printing nothing.
Looks exactly like a failed connection.

## 7. Troubleshooting

**`ssh <host>` times out on one machine but works on another.** A stale
`/etc/hosts` entry pinning the short name to an old LAN IP. `/etc/hosts`
outranks MagicDNS, so only that machine is affected. This is not a general
"short names are broken" problem — diagnose per-host:

```bash
grep -i <host> /etc/hosts
dscacheutil -q host -a name <host>     # macOS
getent hosts <host>                    # Linux
```

**A laptop shows online but refuses connections.** Sleeping. It stays visible in
`tailscale status` while unreachable. `sudo pmset -c sleep 0` on power, or
`caffeinate`.

**A node has an unexpected `-1` suffix in its tailnet name.** An old, offline
node still holds the base name. Delete the dead node in the admin console.

**Convenience aliases** — put in `~/.ssh/config` on every node:

```
Host <alias>
  HostName <host>.<tailnet>.ts.net

Host <alias> <alias2> <alias3>
  User <your-login>
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 4
```

First match wins per keyword, so put specific `HostName` blocks before the
shared options block.
