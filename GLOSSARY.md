# Music LED Strip Control

A server that turns audio into effects and drives LED strips, locally via GPIO or remotely via UDP, with a web UI to configure it.

## Language

**Device**:
One configured output target with its own strip settings, effect state and output type.
_Avoid_: Controller, strip (when meaning the configuration)

**Output**:
The backend that delivers pixel frames of a Device: local GPIO, UDP, or Mock.
_Avoid_: Driver, sink

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

**Diagnosis**:
The structured result of an Output's health check: status, human message and suggested fix.
_Avoid_: Health check
