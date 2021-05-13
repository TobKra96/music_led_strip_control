from libs.webserver.executer_base import ExecuterBase
from libs.notification_enum import NotificationEnum  # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem  # pylint: disable=E0611, E0401

import subprocess
import pyaudio
import wave
import logging
import os
import re


class MicrophoneSettingsExecuter(ExecuterBase):

    def microphone_get_volume(self):
        result = dict()
        try:
            process = subprocess.run(
                ["amixer", "get", "Mic"], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            result["output"] = process.stdout
            result["error"] = process.stderr
            result["returncode"] = process.returncode
            result["level"] = self.get_level_form_output(result["output"])

        except Exception as e:
            self.logger.exception(f"Exeception during mic level down.", e)
            result["level"] = 0
            result["output"] = ""
            result["error"] = "Could not change set mic volume."
            result["returncode"] = 1

        finally:

            return result

    def microphone_set_volume(self, level):
        result = dict()
        try:
            process = subprocess.run(
                ["amixer", "set", "Mic", f"{level}%"], universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            result["output"] = process.stdout
            result["error"] = process.stderr
            result["returncode"] = process.returncode

        except Exception as e:
            self.logger.exception(f"Exeception during mic level up.", e)
            result["output"] = ""
            result["error"] = "Could not change set mic volume."
            result["returncode"] = 1

        finally:
            return result

    def get_level_form_output(self, output):
        if output is None or output is "":
            return 0

        level = 0

        x = re.search("(\d+)?%", output)
        try:
            level = int(x.group(1))
        except Exception as e:
            self.logger.debug("Could not get mic level.")

        return level
