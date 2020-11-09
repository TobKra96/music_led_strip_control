from libs.config_service import ConfigService # pylint: disable=E0611, E0401
from libs.effects_enum import EffectsEnum # pylint: disable=E0611, E0401
from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from libs.fps_limiter import FPSLimiter # pylint: disable=E0611, E0401
from libs.effects.effect_bars import EffectBars # pylint: disable=E0611, E0401
from libs.effects.effect_beat import EffectBeat # pylint: disable=E0611, E0401
from libs.effects.effect_bubble import EffectBubble # pylint: disable=E0611, E0401
from libs.effects.effect_energy import EffectEnergy # pylint: disable=E0611, E0401
from libs.effects.effect_fade import EffectFade # pylint: disable=E0611, E0401
from libs.effects.effect_gradient import EffectGradient # pylint: disable=E0611, E0401
from libs.effects.effect_off import EffectOff # pylint: disable=E0611, E0401
from libs.effects.effect_pendulum import EffectPendulum # pylint: disable=E0611, E0401
from libs.effects.effect_power import EffectPower # pylint: disable=E0611, E0401
from libs.effects.effect_rods import EffectRods # pylint: disable=E0611, E0401
from libs.effects.effect_scroll import EffectScroll # pylint: disable=E0611, E0401
from libs.effects.effect_single import EffectSingle # pylint: disable=E0611, E0401
from libs.effects.effect_slide import EffectSlide # pylint: disable=E0611, E0401
from libs.effects.effect_twinkle import EffectTwinkle # pylint: disable=E0611, E0401
from libs.effects.effect_wave import EffectWave # pylint: disable=E0611, E0401
from libs.effects.effect_wavelength import EffectWavelength # pylint: disable=E0611, E0401
from libs.effects.effect_beat_slide import EffectBeatSlide # pylint: disable=E0611, E0401
from libs.effects.effect_spectrum_analyzer import EffectSpectrumAnalyzer # pylint: disable=E0611, E0401
from libs.effects.effect_vu_meter import EffectVuMeter # pylint: disable=E0611, E0401
from libs.effects.effect_wiggle import EffectWiggle # pylint: disable=E0611, E0401

import numpy as np
import gc as gc
from time import sleep
import time
import cProfile
import random
from collections import deque

# Output array should look like:
# output = {[r1,r2,r3,r4,r5],[g1,g2,g3,g4,g5],[]}

class EffectService():

    def start(self, device):
        """
        Start the effect service process. You can change the effect by add a new effect enum inside the enum_queue.
        """

        print("Start Effect Service component...")
        self._device = device

        self.ten_seconds_counter = time.time()
        self.start_time = time.time()

        self._fps_limiter = FPSLimiter(self._device.device_config["FPS"])

        self._available_effects = {
            EffectsEnum.effect_off: EffectOff,
            EffectsEnum.effect_single:EffectSingle,
            EffectsEnum.effect_gradient:EffectGradient,
            EffectsEnum.effect_fade:EffectFade,
            EffectsEnum.effect_slide:EffectSlide,
            EffectsEnum.effect_bubble:EffectBubble,
            EffectsEnum.effect_twinkle:EffectTwinkle,
            EffectsEnum.effect_pendulum:EffectPendulum,
            EffectsEnum.effect_rods:EffectRods,
            EffectsEnum.effect_scroll:EffectScroll,
            EffectsEnum.effect_energy:EffectEnergy,
            EffectsEnum.effect_wavelength:EffectWavelength,
            EffectsEnum.effect_bars:EffectBars,
            EffectsEnum.effect_power:EffectPower,
            EffectsEnum.effect_beat:EffectBeat,
            EffectsEnum.effect_wave:EffectWave,
            EffectsEnum.effect_beat_slide:EffectBeatSlide,
            EffectsEnum.effect_spectrum_analyzer:EffectSpectrumAnalyzer,
            EffectsEnum.effect_vu_meter:EffectVuMeter,
            EffectsEnum.effect_wiggle:EffectWiggle
        }

        self._initialized_effects = {}
        self._current_effect = {}



        try:
            # Get the last effect and set it. 
            last_effect_string = self._device.device_config["effects"]["last_effect"]
            self._current_effect = EffectsEnum[last_effect_string]

        except Exception:
            print("Could not parse last effect. Set effect to off.")
            self._current_effect = EffectsEnum.effect_off

        
        # A token to cancle the while loop
        self._cancel_token = False
        self._skip_effect = False
        print("Effects component started.")

        while not self._cancel_token:
            #try:
            self.effect_routine()
            #except Exception as e:
            #    print("Error in Effect Service. Routine Restarted. Exception: " + str(e))
            
        print("Effects component stopped.")

    def effect_routine(self):
        # Limit the fps to decrease laggs caused by 100 percent cpu
        self._fps_limiter.fps_limiter()

        # Check the nofitication queue
        if not self._device.device_notification_queue_in.empty():
            self._current_notification_in = self._device.device_notification_queue_in.get()

        if hasattr(self, "_current_notification_in"):
            if self._current_notification_in is NotificationEnum.config_refresh:
                self.refresh()
            elif self._current_notification_in is NotificationEnum.process_continue:
                self._skip_effect = False
            elif self._current_notification_in is NotificationEnum.process_pause:
                self._skip_effect = True
            elif self._current_notification_in is NotificationEnum.process_stop:
                self.stop()

        # Reset the current in notification, to do it only one time.
        self._current_notification_in = None

        #Skip the effect sequence, for example to "pause" the process.
        if self._skip_effect:
            return

        # Check if the effect changed.
        if not self._device.effect_queue.empty():
            new_effect_item = self._device.effect_queue.get()
            self._current_effect = new_effect_item.effect_enum
            print("New effect found:" + str(new_effect_item.effect_enum))

       
        # Something is wrong here, no effect set. So skip until we get a new information.
        if self._current_effect is None:
            print("Effect Service | Could not find effect.")
            return


        if(not(self._current_effect in self._initialized_effects.keys())):
            if self._current_effect in self._available_effects.keys():
                self._initialized_effects[self._current_effect] = self._available_effects[self._current_effect](self._device)
            else:
                print("Could not find effect: " + self._current_effect)
           
        self._initialized_effects[self._current_effect].run()

        self.end_time = time.time()
                            
        if time.time() - self.ten_seconds_counter > 10:
            self.ten_seconds_counter = time.time()
            self.time_dif = self.end_time - self.start_time
            self.fps = 1 / self.time_dif
            print("Effect Service | FPS: " + str(self.fps))

        self.start_time = time.time()

            
    def stop(self):
        
        print("Stopping effect component...")
        self.cancel_token = True

    def refresh(self):
        print("Refresh effects...")
        self._initialized_effects = {}

        self._fps_limiter = FPSLimiter(self._device.device_config["FPS"])
        
        # Notifiy the master component, that I'm finished.
        self._device.device_notification_queue_out.put(NotificationEnum.config_refresh_finished)
        print("Effects refreshed.")

