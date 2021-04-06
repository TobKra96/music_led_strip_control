from libs.audio_device import AudioDevice  # pylint: disable=E0611, E0401

import logging


class AudioInfo:
    def GetAudioDevices(py_audio):
        logger = logging.getLogger(__name__)
        logger.debug("Get audio devices.")
        audio_devices = []

        try:
            audio_device_count = py_audio.get_device_count()
            logger.debug(f"Available audio devices (input and output): {audio_device_count}")

            for i in range(0, audio_device_count):
                try:
                    raw_audio_device = py_audio.get_device_info_by_host_api_device_index(0, i)

                    if raw_audio_device["maxInputChannels"] >= 1:
                        audio_device = AudioInfo.ParseRawAudioDeviceToAudioDevice(raw_audio_device)
                        logger.debug(f"Found audio Device: {audio_device.ToString()}")
                        audio_devices.append(audio_device)
                except Exception as e:
                    logger.debug("Could not get device infos.")
                    logger.exception(f"Unexpected error in AudioInfo: {e}")
        except Exception as e:
            logger.exception(f"Unexpected error in AudioInfo: {e}")

        logger.debug(f"Found {len(audio_devices)} audio devices.")
        return audio_devices

    def GetDefaultAudioDevice(py_audio):
        logger = logging.getLogger(__name__)

        default_device = AudioDevice(0, "Error", 44100)

        try:
            raw_default_device = py_audio.get_default_input_device_info()
            default_device = AudioInfo.ParseRawAudioDeviceToAudioDevice(raw_default_device)

        except Exception as e:
            logger.exception(f"Unexpected error in AudioInfo GetDefaultAudioDevice: {e}")

        return default_device

    def ParseRawAudioDeviceToAudioDevice(raw_audio_device):
        logger = logging.getLogger(__name__)
        id = raw_audio_device["index"]
        name = raw_audio_device["name"]
        defaultSampleRate = raw_audio_device["defaultSampleRate"]

        return AudioDevice(id, name, defaultSampleRate)
