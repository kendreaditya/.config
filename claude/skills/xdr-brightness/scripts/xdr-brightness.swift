// xdr-brightness.swift — HDR brightness booster for MacBook Pro M1/M2/M3
// Compile: swiftc -framework Cocoa -framework IOKit -framework MetalKit xdr-brightness.swift -o xdr-brightness
//
// Usage:
//   xdr-brightness on [0-100]   # boost brightness (default 100%). runs until killed.
//   xdr-brightness off          # kill running instance, restore brightness
//   xdr-brightness status       # print current lux + whether boost is active
//   xdr-brightness auto [0-100] # auto-enable boost when outdoors (lux > 5000)
//
// Background: append --bg to any command to detach from terminal.
//   xdr-brightness on 80 --bg
//   xdr-brightness auto --bg
//
// PID file: /tmp/xdr-brightness.pid

import Cocoa
import Metal
import MetalKit
import QuartzCore
import IOKit

// MARK: - Helpers

let kPidFile = "/tmp/xdr-brightness.pid"
let kTableSize: UInt32 = 256

// Lux thresholds for auto mode
let kLuxOnThreshold: Float  = 5000   // enable boost above this  (~bright indoor/outdoor)
let kLuxOffThreshold: Float = 2000   // disable boost below this  (hysteresis band)

struct GammaSnapshot { var r, g, b: [CGGammaValue] }

func captureGamma(_ id: CGDirectDisplayID) -> GammaSnapshot? {
    var r = [CGGammaValue](repeating: 0, count: Int(kTableSize))
    var g = [CGGammaValue](repeating: 0, count: Int(kTableSize))
    var b = [CGGammaValue](repeating: 0, count: Int(kTableSize))
    var n: UInt32 = 0
    guard CGGetDisplayTransferByTable(id, kTableSize, &r, &g, &b, &n) == .success else { return nil }
    return GammaSnapshot(r: r, g: g, b: b)
}

func applyGamma(_ id: CGDirectDisplayID, snap: GammaSnapshot, factor: Float) {
    var r = snap.r.map { $0 * CGGammaValue(factor) }
    var g = snap.g.map { $0 * CGGammaValue(factor) }
    var b = snap.b.map { $0 * CGGammaValue(factor) }
    CGSetDisplayTransferByTable(id, kTableSize, &r, &g, &b)
}

func modelIdentifier() -> String? {
    let svc = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOPlatformExpertDevice"))
    defer { IOObjectRelease(svc) }
    guard let data = IORegistryEntryCreateCFProperty(svc, "model" as CFString, kCFAllocatorDefault, 0)
        .takeRetainedValue() as? Data else { return nil }
    return String(data: data, encoding: .utf8)?.trimmingCharacters(in: .controlCharacters)
}

// M1 Pro/Max 14"/16" with 600-nit SDR panels use a slightly lower ceiling
let maxGamma: Float = ["MacBookPro18,3", "MacBookPro18,4"].contains(modelIdentifier() ?? "") ? 1.535 : 1.59

/// Read ambient lux directly from the AppleSPUHIDDriver IORegistry property.
/// No entitlements required — works on all Apple Silicon Macs.
func readCurrentLux() -> Float? {
    var iter: io_iterator_t = 0
    IOServiceGetMatchingServices(kIOMainPortDefault, IOServiceMatching("AppleSPUHIDDriver"), &iter)
    defer { IOObjectRelease(iter) }
    var svc = IOIteratorNext(iter)
    while svc != 0 {
        defer { IOObjectRelease(svc); svc = IOIteratorNext(iter) }
        guard let usageRef = IORegistryEntryCreateCFProperty(svc, "PrimaryUsage" as CFString, kCFAllocatorDefault, 0)?.takeRetainedValue() as? Int,
              usageRef == 4,  // 4 = ALS sensor
              let luxRef = IORegistryEntryCreateCFProperty(svc, "CurrentLux" as CFString, kCFAllocatorDefault, 0)?.takeRetainedValue() as? Float
        else { continue }
        return luxRef
    }
    return nil
}

// MARK: - CLI dispatch (non-app commands)

let args = CommandLine.arguments
let cmd  = args.count > 1 ? args[1] : "on"

// status: no app needed
if cmd == "status" {
    let lux = readCurrentLux().map { String(format: "%.0f lux", $0) } ?? "unavailable"
    let pidStr = (try? String(contentsOfFile: kPidFile, encoding: .utf8))?.trimmingCharacters(in: .whitespacesAndNewlines)
    var running = false
    var pidDesc = "no"
    if let p = pidStr, let pid = Int32(p) {
        // kill(pid, 0) returns 0 if the process exists
        running = kill(pid, 0) == 0
        if running { pidDesc = "yes (PID \(pid))" }
    }
    print("Ambient light : \(lux)")
    print("Boost active  : \(pidDesc)")
    exit(0)
}

// off: kill existing instance
if cmd == "off" {
    if let pidStr = try? String(contentsOfFile: kPidFile, encoding: .utf8).trimmingCharacters(in: .whitespacesAndNewlines),
       let pid = Int32(pidStr) {
        kill(pid, SIGKILL)
        try? FileManager.default.removeItem(atPath: kPidFile)
        print("Stopped (PID \(pid)), brightness restored.")
    } else {
        print("No running instance found.")
    }
    exit(0)
}

// MARK: - Background fork via re-exec

let isChild = args.contains("--child")
let background = args.contains("--bg")

if background && !isChild {
    let childArgs = args.dropFirst().filter { $0 != "--bg" } + ["--child"]
    let proc = Process()
    // Resolve full path: args[0] may be a bare name when invoked via PATH
    let selfPath: String
    if args[0].hasPrefix("/") {
        selfPath = args[0]
    } else if let resolved = ProcessInfo.processInfo.environment["_"] {
        selfPath = resolved
    } else {
        // fall back to searching PATH
        let which = Process()
        which.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        which.arguments = [args[0]]
        let pipe = Pipe()
        which.standardOutput = pipe
        try? which.run(); which.waitUntilExit()
        selfPath = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8)?
            .trimmingCharacters(in: .whitespacesAndNewlines) ?? args[0]
    }
    proc.executableURL = URL(fileURLWithPath: selfPath)
    proc.arguments = Array(childArgs)
    try! proc.run()
    print("xdr-brightness running in background (PID \(proc.processIdentifier))")
    print("Stop with: xdr-brightness off")
    exit(0)
}

if isChild {
    let pidStr = "\(ProcessInfo.processInfo.processIdentifier)\n"
    try? pidStr.write(toFile: kPidFile, atomically: true, encoding: .utf8)
}

// MARK: - Parse brightness %

let pct: Float = args.dropFirst().compactMap { Float($0) }.first.map { max(0, min(100, $0)) / 100.0 } ?? 1.0
let boostFactor = 1.0 + (maxGamma - 1.0) * pct
let autoMode = cmd == "auto"

// MARK: - EDR overlay view (renders HDR clear color to trigger EDR mode)

class EDROverlay: MTKView, MTKViewDelegate {
    private var commandQueue: MTLCommandQueue?

    init() {
        super.init(frame: CGRect(x: 0, y: 0, width: 1, height: 1), device: MTLCreateSystemDefaultDevice())
        guard let device else { fatalError("No Metal device") }
        commandQueue = device.makeCommandQueue()
        delegate = self
        colorPixelFormat = .rgba16Float
        colorspace = CGColorSpace(name: CGColorSpace.extendedLinearSRGB)
        clearColor = MTLClearColorMake(1.0, 1.0, 1.0, 1.0)
        preferredFramesPerSecond = 5
        autoResizeDrawable = false
        drawableSize = CGSize(width: 1, height: 1)
        if let layer = self.layer as? CAMetalLayer {
            layer.wantsExtendedDynamicRangeContent = true
            layer.isOpaque = false
            layer.pixelFormat = .rgba16Float
        }
    }
    required init(coder: NSCoder) { fatalError() }

    func draw(in view: MTKView) {
        guard let commandQueue,
              let desc = view.currentRenderPassDescriptor,
              let buf = commandQueue.makeCommandBuffer(),
              let enc = buf.makeRenderCommandEncoder(descriptor: desc)
        else { return }
        enc.endEncoding()
        if let drawable = view.currentDrawable { buf.present(drawable) }
        buf.commit()
    }
    func mtkView(_ view: MTKView, drawableSizeWillChange size: CGSize) {}
}

// MARK: - App delegate

class AppDelegate: NSObject, NSApplicationDelegate {
    var windows:      [NSWindow] = []
    var overlays:     [EDROverlay] = []
    var snapshots:    [CGDirectDisplayID: GammaSnapshot] = [:]
    var signalSources: [DispatchSourceSignal] = []   // must retain or ARC frees them
    var boostOn = false

    func applicationDidFinishLaunching(_ n: Notification) {
        NSApp.setActivationPolicy(.prohibited)

        for screen in NSScreen.screens {
            guard let id = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? CGDirectDisplayID
            else { continue }
            if let snap = captureGamma(id) { snapshots[id] = snap }

            // 1×1 invisible window with EDR MTKView — renders HDR content to trigger EDR mode
            let win = NSWindow(
                contentRect: NSRect(x: screen.frame.origin.x,
                                    y: screen.frame.origin.y + screen.frame.height - 1,
                                    width: 1, height: 1),
                styleMask: [], backing: .buffered, defer: false)
            win.level              = NSWindow.Level(rawValue: Int(CGShieldingWindowLevel()))
            win.collectionBehavior = [.stationary, .canJoinAllSpaces, .ignoresCycle]
            win.isOpaque           = false
            win.hasShadow          = false
            win.backgroundColor    = .clear
            win.ignoresMouseEvents = true
            win.isReleasedWhenClosed = false
            win.hidesOnDeactivate  = false

            let overlay = EDROverlay()
            win.contentView = overlay
            win.orderFrontRegardless()
            windows.append(win)
            overlays.append(overlay)
        }

        // Signal handlers for clean restore — stored in signalSources to prevent ARC deallocation
        for sig in [SIGINT, SIGTERM] {
            signal(sig, SIG_IGN)
            let src = DispatchSource.makeSignalSource(signal: sig, queue: .main)
            src.setEventHandler { self.restore() }
            src.resume()
            signalSources.append(src)
        }

        if autoMode {
            print("xdr-brightness: auto mode — polling ALS every 5s (on > \(Int(kLuxOnThreshold)) lux, off < \(Int(kLuxOffThreshold)) lux)")
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) { self.pollALS() }
            Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { _ in self.pollALS() }
        } else {
            // Apply gamma after a delay to let EDR mode activate
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { self.enableBoost() }
            print("xdr-brightness: \(Int(pct * 100))% boost (factor \(String(format: "%.3f", boostFactor))x). Ctrl-C to stop.")
        }
    }

    func enableBoost() {
        guard !boostOn else { return }
        boostOn = true
        for screen in NSScreen.screens {
            guard let id = screen.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? CGDirectDisplayID,
                  let snap = snapshots[id] else { continue }
            applyGamma(id, snap: snap, factor: boostFactor)
        }
        if autoMode { print("  → boost ON  (\(readCurrentLux().map { String(format: "%.0f lux", $0) } ?? "?"))") }
    }

    func disableBoost() {
        guard boostOn else { return }
        boostOn = false
        for (id, snap) in snapshots { applyGamma(id, snap: snap, factor: 1.0) }
        if autoMode { print("  → boost OFF (\(readCurrentLux().map { String(format: "%.0f lux", $0) } ?? "?"))") }
    }

    func pollALS() {
        guard let lux = readCurrentLux() else { return }
        if !boostOn && lux > kLuxOnThreshold  { enableBoost() }
        if  boostOn && lux < kLuxOffThreshold { disableBoost() }
    }

    func restore() {
        CGDisplayRestoreColorSyncSettings()
        try? FileManager.default.removeItem(atPath: kPidFile)
        exit(0)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
