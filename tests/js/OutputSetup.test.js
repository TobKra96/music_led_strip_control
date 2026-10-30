import { expect, it } from 'vitest';
import { outputPatch, powerEstimate, speedEstimate, splitForm, stateFrom } from '../../src/mlsc/app/static/assets/js/classes/OutputSetup.js';

const settings = () => ({
    output_type: 'output_raspi', chip_family: 'ws2812', colour_order: 'grb', white_channel: false, led_count: 100, led_mid: 50, led_brightness: 100,
    power_limit: { enabled: true, supply_amps: 5, ma_per_led: 60, mode: 'warn' },
    output: {
        output_raspi: { led_pin: 18, led_channel: 0, led_dma: 10, led_freq_hz: 800000, led_invert: false },
        output_udp: { udp_client_ip: '10.0.0.2', udp_client_port: 7777 },
    },
});

it('reads the wizard state from the stored settings and defaults the supply to 5 V', () => {
    const state = stateFrom(settings());

    expect(state).toMatchObject({ output_type: 'output_raspi', led_pin: 18, udp_client_ip: '10.0.0.2', supply_volts: 5, power_enabled: true });
});

it('sends only the settings of the chosen output type', () => {
    const state = stateFrom(settings());

    expect(Object.keys(outputPatch(state).output)).toEqual(['output_raspi']);
    expect(Object.keys(outputPatch({ ...state, output_type: 'output_udp' }).output)).toEqual(['output_udp']);
    expect(outputPatch({ ...state, output_type: 'output_dummy' }).output).toEqual({});
});

it('drops the white channel of a chip that has none and keeps the middle on the strip', () => {
    const patch = outputPatch({ ...stateFrom(settings()), white_channel: true, led_count: 30, led_mid: 80 });

    expect(patch.white_channel).toBe(false);
    expect(patch.led_mid).toBe(29);
    expect(outputPatch({ ...stateFrom(settings()), chip_family: 'sk6812', white_channel: true }).white_channel).toBe(true);
});

it('estimates the draw and warns only when the limit is on and the supply is too small', () => {
    const state = { ...stateFrom(settings()), led_count: 124 };

    expect(powerEstimate(state).amps).toBeCloseTo(7.44);
    expect(powerEstimate(state).warning).toContain('7.4 A');
    expect(powerEstimate({ ...state, power_enabled: false }).warning).toBeNull();
    expect(powerEstimate({ ...state, supply_volts: 12 }).watts).toBeCloseTo(7.44 * 12);
});

it('estimates the frame rate and suggests splitting a long strip', () => {
    expect(speedEstimate(100)).toEqual({ fps: 256, suggestion: null });
    expect(speedEstimate(900).suggestion).toContain('Split');
    expect(speedEstimate(0)).toEqual({ fps: null, suggestion: null });
});

it('splits the flat form into what is applied safely and what is saved directly', () => {
    const output = { output_raspi: { led_pin: 18 } };

    expect(splitForm({ device_name: 'Desk', fps: 60, led_count: 50, colour_order: 'rgb' }, output)).toEqual({
        apply: { output, led_count: 50, colour_order: 'rgb' },
        save: { device_name: 'Desk', fps: 60 },
    });
});
