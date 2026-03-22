---
name: caffeinate
description: Prevent macOS from sleeping using the built-in caffeinate CLI. Use when the user wants to: keep the Mac awake, prevent sleep, keep the display on, close the lid without sleeping, run long tasks without interruption, keep a process running while away, or asks about caffeinate.
---

# caffeinate

Built-in macOS CLI — no installation needed.

## Common commands

```bash
caffeinate &              # prevent idle sleep, background (Ctrl-C or kill to stop)
caffeinate -d &           # also keep display on
caffeinate -s &           # prevent sleep even with lid closed (requires AC power)
caffeinate -t 3600        # caffeinate for exactly N seconds then exit
caffeinate -w <PID>       # stay awake until another process exits
caffeinate ./script.sh    # run a command and stay awake until it finishes
killall caffeinate        # stop all caffeinate instances
```

## Flags

| Flag | Effect |
|------|--------|
| `-i` | Prevent idle sleep (default) |
| `-d` | Prevent display sleep |
| `-s` | Prevent system sleep (lid close) — AC power only |
| `-u` | Declare user active (keeps display on briefly) |
| `-t N` | Limit to N seconds |
| `-w PID` | Exit when process PID exits |

## Lid-close workflow (keep Mac awake with lid closed)

Requires tmux to maintain terminal sessions across lid close:

```bash
tmux new -s work          # start session
# ... start Claude Code or other work ...
# Press Ctrl-B then D to detach
caffeinate -s &           # prevent sleep on lid close (plug in power first)
# close lid safely
# later: open lid, then:
tmux attach -t work       # reconnect
killall caffeinate        # stop when done
```

## Pair with xdr-brightness (outdoor use)

```bash
caffeinate -ds &
xdr-brightness on 100 --bg
```
