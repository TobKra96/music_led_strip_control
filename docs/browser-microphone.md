# Browser Microphone

Use the microphone of the device you browse with, for example a phone, as MLSC's audio input.
Open **Settings → Microphone** in that browser, choose the source **This browser** and press **Stream from this browser**. MLSC selects the Browser Microphone for you.
To go back to a microphone on the server, choose the source **Server device**, pick a device and press **Save**.
The line at the top of the Input card always says what MLSC listens to, for example **Listening to: this browser (not streaming yet)**.

Capture never starts by itself. After a reload or a closed tab, press the button again. Only one browser can stream at a time.

## Browsers need HTTPS

Browsers only allow microphone access on `https://` pages or on `localhost`. A page opened as `http://raspberrypi.local:8080` shows
"The browser only allows microphone access on HTTPS or localhost". Pick one of the two ways below.

### Option 1: MLSC serves HTTPS itself

1. Install the extra: `pip install 'music-led-strip-control[https]'`.
2. Set `"https_port": 8443` in `general_settings` of `config.json` and restart MLSC. `null` or no entry keeps HTTPS off.
3. Open `https://raspberrypi.local:8443`. MLSC creates a self-signed certificate on first start in its data directory (`tls/`).
   The browser warns once that it is not trusted; accept it for this address.

Plain HTTP on the normal port keeps working.

### Option 2: a reverse proxy

If you already run a proxy with a real certificate, put MLSC behind it. With Caddy:

```
mlsc.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

Open `https://mlsc.example.com`. The proxy must not buffer request bodies for `/api/v2/microphone/browser/`.

## Things to know

- **Delay.** The audio travels as small HTTP requests (about 40 ms each) through a buffer of about 100 ms.
  Expect 150 to 250 ms from sound to LEDs, more than with a USB microphone on the server.
  When a request is late, MLSC plays silence for a moment and carries on as soon as about 60 ms of audio is back, without
  waiting for the whole 100 ms again. A lost chunk is bridged with a short fade-out. If the buffer passes 250 ms, it is cut
  back to about 175 ms with a short crossfade instead of an abrupt jump.
- **Keep the page open.** Phones pause background tabs and lock screens. MLSC asks the browser to keep the screen on where it can.
- **Unstable connection.** The Microphone page says so when audio keeps dropping out. Move closer to the router or use 5 GHz Wi-Fi.
- **Sign-in.** When PIN or login protection is on, the stream needs the same session. If it ends, MLSC stops capturing and shows why.
- **No echo cancellation, noise suppression or automatic gain.** They would distort the music, so MLSC turns them off.

## Measuring the delay on a Raspberry Pi 4

The expected delay is an estimate until measured on the device. To measure it:

1. Play a short click or a metronome on a speaker next to the phone and the LED strip.
2. Film both with a phone at 120 fps or more (slow motion).
3. Count frames between the sound's visible waveform and the LED reacting, divided by the frame rate.
4. Repeat for the USB microphone on the server and subtract it to get the extra delay of the Browser Microphone.

If the result is clearly above 250 ms on a good network, a WebSocket transport is the planned fallback.
