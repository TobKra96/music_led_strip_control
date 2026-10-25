# Music LED Strip Control

A server that turns audio into effects and drives LED strips, locally via GPIO or remotely via UDP, with a web UI to configure it.

## Language

**Device**:
One configured output target with its own strip settings, effect state and output type.
_Avoid_: Controller, strip (when meaning the configuration)

**Output**:
The backend that delivers pixel frames of a Device: local GPIO, UDP, or Mock.
_Avoid_: Driver, sink

**GPIO Backend**:
The library or driver that a local GPIO Output uses to push pixel frames to the strip on a given Pi model.
_Avoid_: Driver, GPIO output

**Monitor Device**:
An audio input device that carries audio played by the system or received from a remote source, rather than a microphone.
_Avoid_: Loopback, Virtual mic

**Audio Source**:
Where MLSC takes its audio from: a Server Device (an audio device on the machine MLSC runs on) or the Browser Microphone. Chosen on the Microphone page as "Server device" or "This browser".
_Avoid_: Input type

**Browser Microphone**:
An audio source whose samples are streamed to the server from the microphone of a connected client's browser.
_Avoid_: Web mic, Remote mic

**Mock Output**:
An Output that drives no hardware and only feeds the Strip Preview.
_Avoid_: Dummy

**Strip Preview**:
A live in-browser rendering of the pixel frames a Device produces.
_Avoid_: Simulator

**Chip Family**:
The LED controller type of a strip (WS2812, WS2811, SK6812).
_Avoid_: Strip type

**Colour Order**:
The sequence in which a strip expects its colour channels (for example GRB).
_Avoid_: Pixel format

**Setup Wizard**:
The guided, per-Device flow that configures hardware, Chip Family, Colour Order, LED count and power, and verifies them with Test Patterns.
_Avoid_: Onboarding

**Test Pattern**:
A temporary, server-driven pattern that takes over a Device's strip to verify its setup and then restores the previous effect.
_Avoid_: Test mode

**Power Limit**:
An advisory cap derived from supply amps and per-LED current that warns about, or optionally limits, brightness.
_Avoid_: Brightness limit

**Hotspot**:
The Pi's own Wi-Fi network, which the user can choose as a saved mode when no router is available.
_Avoid_: Access point, AP

**Setup Fallback**:
An automatic, temporary Hotspot raised when the Pi has no usable connection, so the user can reach the UI and join a network. Never saved as the Wi-Fi mode.
_Avoid_: Setup mode, rescue AP

**Wi-Fi Rollback**:
The timed return to the previous Wi-Fi mode when a change to it does not result in a working connection.
_Avoid_: Undo

**Operation**:
A tracked change that can take time or fail, such as applying an Output, microphone or Wi-Fi change, and that ends confirmed, rolled back or failed.
_Avoid_: Job, Task

**Diagnosis**:
The structured result of an Output's health check: status, human message and suggested fix.
_Avoid_: Health check

**Config Migration**:
The one-time, backed-up conversion of an older configuration to the current format, which never alters the original file.
_Avoid_: Upgrade, converter

**Migration Report**:
The structured record of what a Config Migration changed and which values could not be carried over exactly.
_Avoid_: Migration log
