---
name: xdr-brightness
description: Boost MacBook Pro M1/M2/M3 display brightness beyond the system maximum (~500 nits SDR cap) into HDR/XDR range (~1000 nits). Uses a compiled single-file Swift CLI. Trigger when the user asks to: boost screen brightness, make the display brighter, enable XDR/HDR brightness, turn on extra brightness for outdoor use, auto-adjust brightness based on ambient light, or control the xdr-brightness tool.
---

# xdr-brightness

Single-file Swift CLI that unlocks the MacBook Pro's HDR brightness headroom via two mechanisms:
1. An invisible 1×1 Metal window with `wantsExtendedDynamicRangeContent = true` — triggers EDR mode on the panel (~1000 nit budget vs ~500 nit SDR)
2. Gamma table scaling (`CGSetDisplayTransferByTable`) multiplied by a factor up to 1.59×

Ambient light is read directly from `AppleSPUHIDDriver.CurrentLux` in IORegistry — no entitlements needed.

## Binary

Pre-built binary at `scripts/xdr-brightness`. Swift source at `scripts/xdr-brightness.swift`.

## Commands

```bash
xdr-brightness on [0-100]   # boost on at given % (default 100). blocks until killed.
xdr-brightness on 80 --bg   # same, detached to background
xdr-brightness off          # kill background instance, restore brightness
xdr-brightness status       # print ambient lux + whether boost is active
xdr-brightness auto --bg    # auto-enable when lux > 5000, disable when < 2000
```

## Workflow

**Turn on:**
```bash
~/.claude/skills/xdr-brightness/scripts/xdr-brightness on 100 --bg
```

**Check:**
```bash
~/.claude/skills/xdr-brightness/scripts/xdr-brightness status
```

**Turn off:**
```bash
~/.claude/skills/xdr-brightness/scripts/xdr-brightness off
```

**Auto mode** — polls ALS every 5s, enables above 5000 lux, disables below 2000 lux:
```bash
~/.claude/skills/xdr-brightness/scripts/xdr-brightness auto --bg
```

## Recompile if needed

```bash
cd ~/.claude/skills/xdr-brightness/scripts
swiftc -framework Cocoa -framework IOKit -framework MetalKit xdr-brightness.swift -o xdr-brightness
```

## Notes

- Apple Silicon MacBook Pro only (M1/M2/M3 XDR display)
- Process must stay alive to hold EDR mode — PID written to `/tmp/xdr-brightness.pid`
- Boost is lost on reboot; re-run to re-enable
- Max factor: 1.59× (1.535× on MacBookPro18,3/18,4 600-nit panels)
