# Remote audio input options (ticket #223)

Planning research for v3.0. Primary sources only (project READMEs/docs/source, vendor terms). Items the sources did not state are marked **unverified**. Research date: 2026-10-23.

## Current state

MLSC captures audio through PyAudio `input=True` on a selected input device, mono int16 (`server/libs/audio_process_service.py`). Anything that appears as an ALSA/PulseAudio/PipeWire input device (a loopback/monitor) works with no code change. Anything delivered as a raw PCM pipe or socket would need a new input source in the audio service.

## Summary table

| Option | Role | Tap decoded PCM | Pip/web-UI setup | License / ToS | Latency |
|---|---|---|---|---|---|
| librespot / raspotify / spotifyd | Spotify Connect receiver | `pipe` backend (stdout or file), or sound-server sink + monitor | No: separate Rust binary / deb package / systemd daemon | MIT (librespot, raspotify); Premium only; Spotify says use is "probably forbidden" | not stated by sources |
| shairport-sync | AirPlay 1/2 receiver | `pipe` backend (build flag), or sound-server sink | No: C build / distro package, AirPlay 2 needs NQPTP | MIT-style | AirPlay sender sets ~2.0-2.25 s (classic), ~0.5 s (AirPlay 2) |
| Bluetooth A2DP | Phone streams to Pi | Not raw: BlueZ registers endpoints, the sound server decodes; capture the sink monitor | Pairing via BlueZ/D-Bus; no pip story | n/a (BlueZ) | not stated by sources |
| PulseAudio/PipeWire network | Remote machine streams to Pi | Appears as a normal source/sink | Config files, no pip | n/a | RTP default 100 ms (`sess.latency.msec`) |
| Snapcast | Multiroom sync | Server reads PCM sources; client `file` backend can write stdout | No: separate server/client | GPLv3 | Client ALSA `buffer_time` default 80 ms, plus configured stream buffer |

## Spotify Connect (librespot, raspotify, spotifyd)

- librespot is an open-source Spotify client that can act as a Connect receiver; it "only works with Spotify Premium" and will not add free-account support. [librespot README](https://github.com/librespot-org/librespot/blob/dev/README.md)
- Backends: Rodio (default), ALSA, GStreamer, PortAudio, PulseAudio, JACK, SDL, **Pipe**, **Subprocess**. Build needs Rust/Cargo and, on Debian, `build-essential` and `libasound2-dev`. Same README.
- The pipe backend writes decoded bytes unchanged to stdout, or to a file when a device name is given (`--backend pipe --device <file>`); it logs the format but sets no rate/channels itself. [pipe.rs](https://github.com/librespot-org/librespot/blob/dev/playback/src/audio_backend/pipe.rs) Exact PCM format (expected 44.1 kHz stereo S16) is **unverified** from these sources.
- raspotify packages librespot (slightly modified) as a systemd daemon, installed by a curl script or `.deb`; arm64/armhf/amd64/riscv64, not ARMv6 (Pi 1 / Zero 1). Audio configuration lives in its wiki, not the README. [raspotify README](https://github.com/dtcooper/raspotify/blob/master/README.md)
- spotifyd is a daemon with Connect support, requires Premium; its README defers backends and config to its wiki (backend list **unverified**). [spotifyd README](https://github.com/Spotifyd/spotifyd/blob/master/README.md)
- Licensing/ToS: librespot code is MIT, but its own disclaimer says connecting to Spotify's API this way is "probably forbidden by them", use at own risk. Spotify's Developer Terms prohibit "stream ripping" or other capture (IV.2.b.iii), and prohibit using Spotify Content to train ML/AI models (IV.2.a.i). Those terms govern the official Platform; librespot does not use it, but they show Spotify's stance on capturing streamed content. Real-time audio analysis for LED output is not addressed by name (**unverified legal reading**). [Spotify Developer Terms](https://developer.spotify.com/terms)

## AirPlay (shairport-sync)

- Builds as AirPlay 2 (some limitations) or classic AirPlay 1. AirPlay 2 needs the companion NQPTP for timing. [README](https://github.com/mikebrady/shairport-sync/blob/master/README.md)
- Output backends: ALSA, sndio, PipeWire, PulseAudio, macOS, plus unix pipe or STDOUT. Metadata via pipe/UDP, MQTT, MPRIS-like, D-Bus. Same README.
- Pipe backend needs `--with-pipe`; defaults to `/tmp/shairport-sync-audio`; set a single `output_rate` (44100 classic / 48000 AirPlay 2), `output_format` (S16_LE / S32_LE) and `output_channels = 2` to avoid silent format switching. [sample config](https://github.com/mikebrady/shairport-sync/blob/master/scripts/shairport-sync.conf)
- Latency: classic sources typically set about 2.0-2.25 s, AirPlay 2 about 0.5 s (README). The backend buffer defaults to 0.2 s and `audio_backend_latency_offset_in_seconds` shifts timing (sample config). Whether the pipe output is time-aligned with what speakers would play is **unverified**.
- License: copyright notice with MIT-style permission text; bundled parts have their own licenses. [LICENSES](https://github.com/mikebrady/shairport-sync/blob/master/LICENSES)

## Bluetooth A2DP

- BlueZ's Media API (`org.bluez.Media1`) lets an application register local media endpoints (UUID, codec, capabilities) over D-Bus. [org.bluez.Media](https://github.com/bluez/bluez/blob/master/doc/org.bluez.Media.rst) The page does not name A2DP and does not describe PCM delivery.
- In practice the sound server (PipeWire/PulseAudio) owns the endpoint and exposes decoded audio as a node; MLSC would then capture its monitor. That integration is **unverified** here (no primary page fetched for PipeWire's BlueZ module). Pairing/trust is a BlueZ operation (could be driven over D-Bus from a web UI; not pip-installable).

## PulseAudio / PipeWire network

- PipeWire implements the PulseAudio server (`libpipewire-module-protocol-pulse`); `server.address` can include `tcp:4713` (all addresses) or a single address; network clients default to restricted permissions. [docs](https://docs.pipewire.org/page_module_protocol_pulse.html)
- `libpipewire-module-rtp-source` creates a source that receives RTP (raw PCM, Opus, MIDI); defaults `source.ip` 224.0.0.56, `sess.latency.msec` 100. [docs](https://docs.pipewire.org/page_module_rtp_source.html)
- PulseAudio's network doc (freedesktop wiki) returned HTTP 403 and was not read: PulseAudio module details are **unverified**.
- The resulting source shows up as a normal input device, so MLSC needs no code change; setup is system configuration only.

## Snapcast

- Snapserver reads PCM from sources (`pipe`, `librespot`, `airplay`, `alsa`, `tcp`), encodes (FLAC default, PCM, Vorbis, Opus), timestamps, and sends over TCP; clients sync clocks and play at the scheduled time. JSON-RPC control over TCP/HTTP/WebSocket, with a bundled web app. Client ALSA `buffer_time` defaults to 80 ms. [Snapcast README](https://github.com/badaix/snapcast/blob/master/README.md)
- A Snapclient on the Pi playing to an ALSA loopback (or the `file` player backend writing to stdout) would feed MLSC. License GPLv3. [LICENSE](https://github.com/badaix/snapcast/blob/master/LICENSE) Mostly relevant if users already run multiroom audio; it also wraps librespot/shairport-sync as sources.

## Findings relevant to 3.0

- No option is installable from pip; all are external daemons. MLSC could at most detect them, document them, and generate/launch config.
- The cheapest universal integration needs no new code: expose the remote audio as a system input (ALSA loopback, Pulse/PipeWire monitor). MLSC already selects an input device in the web UI.
- A built-in "named pipe / TCP PCM source" would be the one code addition covering librespot, shairport-sync and Snapcast. The rate/format/channels must be configured to match the producer.

## Recommendation

1. For 3.0, do not bundle any daemon. Document two supported paths: (a) system loopback/monitor device (works with every option), (b) optionally a generic named-pipe PCM input source in the audio service.
2. Treat shairport-sync and PipeWire RTP / Snapcast as the lower-risk guides; list Spotify via raspotify/librespot as "user's responsibility" given the stated ToS risk and Premium requirement.
3. Treat Bluetooth A2DP as OS-level pairing plus monitor capture.

## Open uncertainties

- Exact PCM format librespot's pipe emits, and spotifyd's backend list (wiki not read).
- PulseAudio network module behaviour (wiki returned 403).
- BlueZ-to-PipeWire A2DP capture path; end-to-end latency for Bluetooth, librespot and Snapcast (no figures in the sources fetched).
- Legal reading of Spotify terms for visualization-only use of a Connect receiver.
- Whether PyAudio on the Pi opens PipeWire monitors reliably (not tested).
