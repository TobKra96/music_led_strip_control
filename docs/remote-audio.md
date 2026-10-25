# Remote audio

MLSC can visualize audio that reaches the Pi from another device: AirPlay, Bluetooth, a network stream or Spotify. MLSC has no remote input of its own. The Pi plays the remote audio into a **Monitor Device**, and MLSC listens to that device like a microphone.

MLSC does not install, start or configure any of the programs below. Each recipe is a pointer; the program's own documentation is the authority, and you maintain the setup.

## How it works

```
phone / laptop ──► receiver on the Pi ──► ALSA loopback ──► MLSC
                   (shairport-sync,       (Monitor Device)
                    BlueALSA, PipeWire,
                    raspotify)
```

1. A receiver program on the Pi plays the audio to the playback side of the ALSA loopback, `hw:Loopback,0`.
2. The loopback hands the same audio to its capture side, `hw:Loopback,1`.
3. On the **Microphone** page you set the source to **Server device** and select that capture side, the Monitor Device, which is tagged **Monitor**.

MLSC runs as a system service under `root`, so it cannot open the sound server of a logged-in desktop user. Routing the audio into the ALSA loopback works the same with or without a desktop.

## Set up the Monitor Device

Load the ALSA loopback driver, and load it on every boot:

```bash
sudo modprobe snd-aloop
echo snd-aloop | sudo tee /etc/modules-load.d/snd-aloop.conf
```

Check that the card exists:

```bash
aplay -l | grep Loopback
```

MLSC reads the device list when it starts, so restart it:

```bash
sudo systemctl restart mlsc
```

On the **Microphone** page, choose the source **Server device**, then pick the device named like `Loopback: PCM (hw:2,1)`, the one ending in `,1`, tagged **Monitor**. Press **Test**, play something on the remote device and watch the meter, then **Save**.

### Hear it on your speakers too

Audio sent to the loopback goes to MLSC only. To also play it on the Pi's own output, point the receiver at a device that duplicates the audio. Add this to `/etc/asound.conf`, replacing `hw:Headphones` with your output card from `aplay -l`:

```
pcm.mlsc_tee {
    type plug
    slave.pcm {
        type multi
        slaves.a.pcm "hw:Loopback,0"
        slaves.a.channels 2
        slaves.b.pcm "plughw:Headphones"
        slaves.b.channels 2
        bindings.0 { slave a; channel 0; }
        bindings.1 { slave a; channel 1; }
        bindings.2 { slave b; channel 0; }
        bindings.3 { slave b; channel 1; }
    }
    ttable.0.0 1
    ttable.1.1 1
    ttable.0.2 1
    ttable.1.3 1
}
```

Then use `mlsc_tee` instead of `hw:Loopback,0` in the recipes below. Some sound cards reject a shared clock with the loopback; if playback fails, use the loopback alone.

## AirPlay (shairport-sync)

[shairport-sync](https://github.com/mikebrady/shairport-sync) makes the Pi an AirPlay receiver.

```bash
sudo apt install shairport-sync
```

In `/etc/shairport-sync.conf`, send the output to the loopback:

```
general = {
    name = "LED Strip";
    output_backend = "alsa";
};

alsa = {
    output_device = "hw:Loopback,0";
};
```

```bash
sudo systemctl restart shairport-sync
```

The Pi now shows up as an AirPlay speaker named "LED Strip". AirPlay buffers on purpose, often around 2 seconds, so the LEDs lag behind what the sender itself plays. The distribution package may be built for classic AirPlay only; see the shairport-sync README for an AirPlay 2 build.

## Bluetooth

A phone streams to the Pi over Bluetooth A2DP. On Raspberry Pi OS Lite, [BlueALSA](https://github.com/arkq/bluez-alsa) receives the stream without a desktop sound server.

```bash
sudo apt install bluez-alsa-utils
```

Run the BlueALSA daemon with the A2DP sink profile (`bluealsa -p a2dp-sink`; on most systems through its systemd unit). Then pair the phone:

```bash
bluetoothctl
power on
discoverable on
pairable on
agent on
# pair from the phone, then:
trust XX:XX:XX:XX:XX:XX
```

Play the connected phone into the loopback:

```bash
bluealsa-aplay --pcm=hw:Loopback,0 XX:XX:XX:XX:XX:XX
```

Run `bluealsa-aplay` as a service to keep it running after a reboot. Bluetooth audio adds its own codec delay, which varies by phone.

## PipeWire/PulseAudio network

A Linux computer on your network plays straight to the Pi through the PulseAudio protocol. The Pi runs PipeWire with its PulseAudio server (`pipewire-pulse`), which Raspberry Pi OS desktop has by default.

On the Pi, as the user that runs PipeWire, accept network clients. Create `~/.config/pipewire/pipewire-pulse.conf.d/network.conf`:

```
pulse.properties = {
    server.address = [ "unix:native" "tcp:4713" ]
}
```

PipeWire already offers the loopback card as a sink. Restart the server, find that sink and make it the default:

```bash
systemctl --user restart pipewire-pulse
pactl list short sinks | grep -i loopback
pactl set-default-sink <name of the Loopback sink>
```

On a Pi without a desktop login, run `sudo loginctl enable-linger $USER` so the user's PipeWire keeps running.

On the sending computer, play to the Pi:

```bash
PULSE_SERVER=tcp:raspberrypi.local:4713 mpv song.mp3
```

Port 4713 accepts audio from anyone who can reach it. Open it only on a network you trust.

## Spotify (raspotify)

> **Your responsibility.** Spotify Connect receivers such as raspotify use [librespot](https://github.com/librespot-org/librespot), an unofficial Spotify client. It needs a Spotify **Premium** account, and librespot's own README says that using it is "probably forbidden" by Spotify. MLSC does not endorse or support this setup; you decide whether to use it and carry the risk.

[raspotify](https://github.com/dtcooper/raspotify) packages librespot as a service. It does not run on ARMv6 boards (Pi 1, Pi Zero 1). Install it as its README describes, then in `/etc/raspotify/conf` set:

```
LIBRESPOT_BACKEND=alsa
LIBRESPOT_DEVICE=hw:Loopback,0
```

```bash
sudo systemctl restart raspotify
```

The Pi now shows up as a Spotify Connect device in the Spotify app.

## Troubleshooting

- **Hear what MLSC hears.** After a successful **Test microphone** on the Microphone page, press play under **Play recording: what MLSC hears**. It is the 2 seconds of the test after the device, sample rate and gain, before the effects. It stays in memory, the next test replaces it, and a restart discards it.
- **No device tagged Monitor.** Check `aplay -l | grep Loopback`, then restart MLSC so it reads the device list again.
- **The meter stays flat.** Make sure the receiver plays to `hw:Loopback,0` (playback side) and MLSC listens on the device ending in `,1` (capture side). Something must be playing on the remote device.
- **"Device or resource busy" from the receiver.** Only one program can play to `hw:Loopback,0` at a time, so only one receiver can feed MLSC. Stop the other receiver.
