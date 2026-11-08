import AppKit

// No Dock icon, focus stealing, event taps, or Accessibility permission required.
let app = NSApplication.shared
app.setActivationPolicy(.accessory)

let panel = NSPanel(
    contentRect: NSRect(x: 0, y: 0, width: 800, height: 136),
    styleMask: [.borderless, .nonactivatingPanel],
    backing: .buffered,
    defer: false
)
panel.title = "YTM Desktop Lyrics"
panel.level = .floating
panel.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
panel.isOpaque = false
panel.backgroundColor = .clear
panel.hasShadow = false
panel.ignoresMouseEvents = true
panel.hidesOnDeactivate = false
panel.isReleasedWhenClosed = false

let background = NSView(frame: panel.contentView!.bounds)
background.autoresizingMask = [.width, .height]
background.wantsLayer = true
background.layer?.backgroundColor = NSColor.black.withAlphaComponent(0.72).cgColor
background.layer?.cornerRadius = 18
panel.contentView = background

func lyricLabel(size: CGFloat, color: NSColor) -> NSTextField {
    let label = NSTextField(wrappingLabelWithString: "")
    label.font = .systemFont(ofSize: size, weight: .medium)
    label.textColor = color
    label.alignment = .center
    label.maximumNumberOfLines = 2
    label.translatesAutoresizingMaskIntoConstraints = false
    background.addSubview(label)
    NSLayoutConstraint.activate([
        label.leadingAnchor.constraint(equalTo: background.leadingAnchor, constant: 24),
        label.trailingAnchor.constraint(equalTo: background.trailingAnchor, constant: -24)
    ])
    return label
}

let current = lyricLabel(size: 26, color: .white)
let next = lyricLabel(size: 19, color: NSColor.white.withAlphaComponent(0.65))
NSLayoutConstraint.activate([
    current.topAnchor.constraint(equalTo: background.topAnchor, constant: 18),
    next.topAnchor.constraint(equalTo: current.bottomAnchor, constant: 8)
])

func positionPanel() {
    guard let screen = NSScreen.main ?? NSScreen.screens.first else { return }
    let frame = screen.visibleFrame
    let width = min(860, max(240, frame.width - 64))
    current.preferredMaxLayoutWidth = width - 48
    next.preferredMaxLayoutWidth = width - 48
    let nextHeight = next.stringValue.isEmpty ? 0 : next.intrinsicContentSize.height + 8
    let height = ceil(current.intrinsicContentSize.height + nextHeight + 36)
    panel.setFrame(NSRect(x: frame.midX - width / 2, y: frame.maxY - height - 16,
                         width: width, height: height), display: true)
}
positionPanel()
let screenObserver = NotificationCenter.default.addObserver(
    forName: NSApplication.didChangeScreenParametersNotification, object: nil, queue: .main
) { _ in positionPanel() }
var dismissTimer: Timer?

// Newline-delimited JSON from the Python owner; EOF closes orphaned overlays.
DispatchQueue.global(qos: .userInitiated).async {
    while let line = readLine() {
        guard let data = line.data(using: .utf8),
              let message = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { continue }
        DispatchQueue.main.async {
            dismissTimer?.invalidate()
            dismissTimer = nil
            panel.alphaValue = 1
            if message["visible"] as? Bool == false {
                panel.orderOut(nil)
            } else {
                current.stringValue = message["current"] as? String ?? ""
                next.stringValue = message["next"] as? String ?? ""
                next.isHidden = next.stringValue.isEmpty
                positionPanel()
                panel.orderFrontRegardless()
                if let delay = message["fade_after"] as? Double {
                    let fadeStart = ProcessInfo.processInfo.systemUptime + delay
                    let timer = Timer(timeInterval: 1.0 / 30, repeats: true) { timer in
                        let progress = (ProcessInfo.processInfo.systemUptime - fadeStart) / 0.4
                        panel.alphaValue = max(0, min(1, 1 - progress))
                        if progress >= 1 {
                            timer.invalidate()
                            panel.orderOut(nil)
                        }
                    }
                    timer.fireDate = Date().addingTimeInterval(delay)
                    RunLoop.main.add(timer, forMode: .common)
                    dismissTimer = timer
                }
            }
        }
    }
    DispatchQueue.main.async { app.terminate(nil) }
}
app.run()
