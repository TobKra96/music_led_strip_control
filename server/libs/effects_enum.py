from enum import Enum


class EffectsEnum(Enum):
    effect_off = 1
    effect_single = 2
    effect_gradient = 3
    effect_fade = 4
    effect_sync_fade = 5
    effect_slide = 6
    effect_bubble = 7
    effect_twinkle = 8
    effect_pendulum = 9
    effect_rods = 10
    effect_segment_color = 11
    effect_fireplace = 12
    effect_scroll = 13
    effect_advanced_scroll = 14
    effect_energy = 15
    effect_wavelength = 16
    effect_bars = 17
    effect_power = 18
    effect_beat = 19
    effect_beat_twinkle = 20
    effect_beat_slide = 21
    effect_wave = 22
    effect_wiggle = 23
    effect_vu_meter = 24
    effect_spectrum_analyzer = 25
    effect_direction_changer = 26
    effect_border = 27
    effect_random_cycle = 28
    effect_random_non_music = 29
    effect_random_music = 30
    effect_strobe = 31


class EffectNames():
    non_music = {
        EffectsEnum(2).name: "Single",
        EffectsEnum(3).name: "Gradient",
        EffectsEnum(4).name: "Fade",
        EffectsEnum(5).name: "Sync Fade",
        EffectsEnum(6).name: "Slide",
        EffectsEnum(7).name: "Bubble",
        EffectsEnum(8).name: "Twinkle",
        EffectsEnum(9).name: "Pendulum",
        EffectsEnum(10).name: "Rods",
        EffectsEnum(11).name: "Segment Color",
        EffectsEnum(12).name: "Fireplace",
        EffectsEnum(31).name: "Strobe"
    }

    music = {
        EffectsEnum(13).name: "Scroll",
        EffectsEnum(14).name: "Advanced Scroll",
        EffectsEnum(15).name: "Energy",
        EffectsEnum(16).name: "Wavelength",
        EffectsEnum(17).name: "Bars",
        EffectsEnum(18).name: "Power",
        EffectsEnum(19).name: "Beat",
        EffectsEnum(20).name: "Beat Twinkle",
        EffectsEnum(21).name: "Beat Slide",
        EffectsEnum(22).name: "Wave",
        EffectsEnum(23).name: "Wiggle",
        EffectsEnum(24).name: "VU Meter",
        EffectsEnum(25).name: "Spectrum Analyzer",
        EffectsEnum(26).name: "Direction Changer",
        EffectsEnum(27).name: "Border"
    }

    special = {
        EffectsEnum(1).name: "Off",
        EffectsEnum(28).name: "Random Cycle",
        EffectsEnum(29).name: "Random Non-Music",
        EffectsEnum(30).name: "Random Music"
    }
