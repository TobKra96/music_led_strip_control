const PREVIEW_URL = id => `/api/v2/devices/${id}/preview`;

/**
 * Decode the `frame` of a `preview` event into one `[r, g, b]` triple per LED.
 * @param {string} frame Base64 of the red, green and blue of every LED.
 * @return {Array.<Array.<number>>}
 */
export function decodeFrame(frame) {
    const bytes = Uint8Array.from(atob(frame), c => c.charCodeAt(0));
    const leds = [];
    for (let i = 0; i + 2 < bytes.length; i += 3) leds.push([bytes[i], bytes[i + 1], bytes[i + 2]]);
    return leds;
}

/** A live rendering of the frames of one Device on a canvas. The stream is only open while a device is shown. */
export default class StripPreview {
    /**
     * @param {HTMLCanvasElement} canvas
     * @param {function(number): void} [onFrame] Called with the LED count of every frame.
     */
    constructor(canvas, onFrame) {
        this._canvas = canvas;
        this._onFrame = onFrame;
        /** @type {EventSource|null} */
        this._source = null;
    }

    /** Show the device with this id; a group or `all_devices` shows its first device. */
    show(deviceId) {
        this.stop();
        this._source = new EventSource(PREVIEW_URL(deviceId));
        this._source.addEventListener('preview', e => this._draw(decodeFrame(JSON.parse(e.data).frame)));
    }

    stop() {
        this._source?.close();
        this._source = null;
    }

    _draw(leds) {
        const ctx = this._canvas.getContext('2d');
        const { width, height } = this._canvas;
        const step = width / Math.max(leds.length, 1);
        // The canvas stays transparent, so the card of the page shows through in both themes.
        // The sockets of the LEDs use the text color of the page.
        ctx.clearRect(0, 0, width, height);
        const socket = getComputedStyle(this._canvas).color;
        // Round LEDs while there is room for them, a solid bar otherwise.
        const round = step >= 6;
        const radius = Math.min(step, height) / 2 - 1;
        leds.forEach(([r, g, b], i) => {
            if (round) {
                const x = (i + 0.5) * step;
                ctx.beginPath();
                ctx.arc(x, height / 2, radius, 0, 2 * Math.PI);
                ctx.globalAlpha = 0.15;
                ctx.fillStyle = socket;
                ctx.fill();
                ctx.globalAlpha = 1;
                ctx.fillStyle = `rgb(${r},${g},${b})`;
                ctx.fill();
            } else {
                ctx.globalAlpha = 1;
                ctx.fillStyle = `rgb(${r},${g},${b})`;
                ctx.fillRect(i * step, 0, Math.ceil(step), height);
            }
        });
        this._onFrame?.(leds.length);
    }
}
