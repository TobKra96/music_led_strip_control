from libs.webserver.executer_base import ExecuterBase

from libs.audio_info import AudioInfo  # pylint: disable=E0611, E0401

class GeneralExecuter(ExecuterBase):
    
    def GetColors(self):
        colors = dict()
        for colorID in self._config["colours"]:
            colors[colorID] = colorID
        return colors

    def GetGradients(self):
        gradients = dict()
        for gradientID in self._config["gradients"]:
            gradients[gradientID] = gradientID
        return gradients

    def GetLEDStrips(self):
        led_strips = dict()
        for led_strip_ID in self._config["led_strips"]:
            led_strips[led_strip_ID] = self._config["led_strips"][led_strip_ID]
        return led_strips

    def GetLoggingLevels(self):
        logging_levels = dict()
        for logging_level_ID in self._config["logging_levels"]:
            logging_levels[logging_level_ID] = self._config["logging_levels"][logging_level_ID]
        return logging_levels

    def GetAudioDevices(self):
        audio_devices_dict = dict()
        audio_devices = AudioInfo.GetAudioDevices(self._py_audio)
        for current_audio_device in audio_devices:
            audio_devices_dict[current_audio_device.id] = current_audio_device.ToString()
        return audio_devices_dict

    def GetOutputTypes(self):
        output_types = dict()
        output_types["output_raspi"] = "Output Raspberry Pi"
        output_types["output_udp"] = "Output Network via UDP"
        return output_types