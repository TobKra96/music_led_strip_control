from libs.webserver.executer_base import ExecuterBase
from libs.audio_info import AudioInfo  # pylint: disable=E0611, E0401


class GeneralExecuter(ExecuterBase):

    def get_colors(self):
        colors = dict()
        for colorID in self._config["colors"]:
            colors[colorID] = colorID
        return colors

    def get_gradients(self):
        gradients = dict()
        for gradientID in self._config["gradients"]:
            gradients[gradientID] = gradientID
        return gradients

    def get_led_strips(self):
        led_strips = dict()
        for led_strip_ID in self._config["led_strips"]:
            led_strips[led_strip_ID] = self._config["led_strips"][led_strip_ID]
        return led_strips

    def get_logging_levels(self):
        logging_levels = dict()
        for logging_level_ID in self._config["logging_levels"]:
            logging_levels[logging_level_ID] = self._config["logging_levels"][logging_level_ID]
        return logging_levels

    def get_audio_devices(self):
        audio_devices_dict = dict()
        audio_devices = AudioInfo.get_audio_devices(self._py_audio)
        for current_audio_device in audio_devices:
            audio_devices_dict[current_audio_device.id] = current_audio_device.to_string()
        return audio_devices_dict

    def get_output_types(self):
        output_types = dict()
        output_types["output_raspi"] = "Output Raspberry Pi"
        output_types["output_udp"] = "Output Network via UDP"
        return output_types

    def get_effects(self):
        # Hardcoded effects for now.
        # Todo: Sort effects in json config by type.

        # Unused effects found in config:
        # effect_music
        # effect_spectrum

        effects = dict()
        effects["non_music"] = {
            "effect_single": "Single",
            "effect_gradient": "Gradient",
            "effect_fade": "Fade",
            "effect_sync_fade": "Sync Fade",
            "effect_slide": "Slide",
            "effect_bubble": "Bubble",
            "effect_twinkle": "Twinkle",
            "effect_pendulum": "Pendulum",
            "effect_rods": "Rods",
            "effect_segment_color": "Segment Color",
            "effect_fireplace": "Fireplace",
            "effect_strobe": "Strobe",
        }
        effects["music"] = {
            "effect_scroll": "Scroll",
            "effect_advanced_scroll": "Advanced Scroll",
            "effect_energy": "Energy",
            "effect_wavelength": "Wavelength",
            "effect_bars": "Bars",
            "effect_power": "Power",
            "effect_beat": "Beat",
            "effect_beat_twinkle": "Beat Twinkle",
            "effect_beat_slide": "Beat Slide",
            "effect_wave": "Wave",
            "effect_wiggle": "Wiggle",
            "effect_vu_meter": "VU Meter",
            "effect_spectrum_analyzer": "Spectrum Analyzer",
            "effect_direction_changer": "Direction Changer"
        }

        return effects
