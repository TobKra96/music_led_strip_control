import { expect, it, vi } from 'vitest';
import StripPreview, { decodeFrame } from '../../src/mlsc/app/static/assets/js/classes/StripPreview.js';

it('decodes a frame into one rgb triple per LED', () => {
    expect(decodeFrame(btoa(String.fromCharCode(1, 2, 3, 4, 5, 6)))).toEqual([[1, 2, 3], [4, 5, 6]]);
});

it('draws every LED as a bar and reports the LED count', () => {
    const ctx = { fillRect: vi.fn(), clearRect: vi.fn() };
    const canvas = { width: 600, height: 80, getContext: () => ctx };
    const onFrame = vi.fn();

    new StripPreview(canvas, onFrame)._draw([[255, 0, 0], [0, 255, 0]]);

    expect(ctx.fillRect).toHaveBeenCalledTimes(2);
    expect(onFrame).toHaveBeenCalledWith(2);
});
