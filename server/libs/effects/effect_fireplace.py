from libs.effects.effect import Effect  # pylint: disable=E0611, E0401

from random import randint
from scipy.ndimage.filters import gaussian_filter1d
import numpy as np


class EffectFireplace(Effect):

    def __init__(self, device):
        # Call the constructor of the base class.
        super(EffectFireplace, self).__init__(device)
        # Setup for "EffectFireplace" (don't change this).
        

        self.sparks_area_current_length = 0
        self.sparks_area_target_length = 0
        self.sparks_target_appear_distance = 0
        self.sparks_current_appear_distance = 0

        self.sparks_target_new_spaks_length = 0
        self.sparks_new_sparks_distance = 0

        self.sparks_array = np.zeros((3, self._device.device_config["LED_Count"]))

        self.firebase_area_current_length = 0
        self.firebase_area_target_length = 0

    def run(self):
        #
        #
        #  |     firebase_area      |                      sparks_area                          |                           |
        #  |----*---*-------*-----*-    *       *                 *     *                *                                  |
        #

        # Get the config of the current effect.
        effect_config = self.get_effect_config("effect_fireplace")

        led_count = self._device.device_config["LED_Count"]
        
        # Build an empty array.
        output_array = np.zeros((3, led_count))
       
        firebase_flicker_speed = 5       
        firebase_area_minlength = 10
        firebase_area_maxlength = 40
        
        sparks_flicker_speed = 1
        sparks_fly_speed = 1
        
        sparks_minappear_distance = 20
        sparks_maxappear_distance = 60
        
        sparks_min_length = 2
        sparks_max_length = 6

        sparks_area_minlength = 40
        sparks_area_maxlength = 100

        blur = 0.7
        mask_blur = 0.1
        

        
        firebase_maincolor = self._config_colours[effect_config["firebase_maincolor"]]
        firebase_secondcolor = self._config_colours[effect_config["firebase_secondcolor"]]

        sparks_maincolor = self._config_colours[effect_config["sparks_maincolor"]]
        sparks_secondcolor = self._config_colours[effect_config["sparks_secondcolor"]]

        # Calculate the target area lengths
        if self.firebase_area_target_length == 0 or self.firebase_area_current_length == self.firebase_area_target_length:
            self.firebase_area_target_length = randint(firebase_area_minlength,firebase_area_maxlength)

        if self.sparks_area_target_length == 0 or self.sparks_area_current_length == self.sparks_area_target_length:
            self.sparks_area_target_length = randint(sparks_area_minlength,sparks_area_maxlength)

        # Get the flickering speed of the sparks and the firebase
        firebase_steps = firebase_flicker_speed
        sparks_steps = sparks_flicker_speed

        sparks_fly_speed_randomized = randint(sparks_fly_speed, sparks_fly_speed+2)
        sparks_fly_steps = sparks_fly_speed_randomized

        if sparks_fly_steps > 0:
            # Calculate the new current lenght of the areas.
            self.firebase_area_current_length = self.get_current_length(self.firebase_area_current_length, firebase_steps, self.firebase_area_target_length)
            self.sparks_area_current_length = self.get_current_length(self.sparks_area_current_length, sparks_steps, self.sparks_area_target_length)

            # Init firebase
            firebase_array = np.zeros((3, led_count))
            
            # Set the main color of the firebase
            firebase_array[0][:self.firebase_area_current_length] = firebase_maincolor[0]
            firebase_array[1][:self.firebase_area_current_length] = firebase_maincolor[1]
            firebase_array[2][:self.firebase_area_current_length] = firebase_maincolor[2]
                    

            #
            #                  sparks_target_appear_distance
            #   |                           |                                       |
            #   |                           |                                       |
            #   |   ****************                                                |
            #   |               ******************                                  |
            #   |                           ******************                      |
            #   |***                           ******************                   |
            #   |                              |                                    |
            #   |                              |                                    |
            #                               sparks_current_appear_distance

            # Check if we need to calculate a new spark
            if self.sparks_target_appear_distance == 0 or (self.sparks_current_appear_distance - self.sparks_target_appear_distance) >= self.sparks_target_appear_distance:
                self.sparks_target_new_spaks_length = randint(sparks_min_length, sparks_max_length)
                self.sparks_current_appear_distance = 0
                self.sparks_target_appear_distance = randint(sparks_minappear_distance, sparks_maxappear_distance)

            # rotate the array 
            self.sparks_array[:, sparks_fly_steps:] = self.sparks_array[:, :-sparks_fly_steps]
            self.sparks_array[:, :sparks_fly_steps][0] = 0
            self.sparks_array[:, :sparks_fly_steps][1] = 0
            self.sparks_array[:, :sparks_fly_steps][2] = 0

            self.sparks_current_appear_distance = self.sparks_current_appear_distance + sparks_fly_steps

            #reached the target distance
            if self.sparks_current_appear_distance >= self.sparks_target_appear_distance:
                
                distance_diff =  self.sparks_current_appear_distance - self.sparks_target_appear_distance

                offset = 0
                if distance_diff > self.sparks_target_new_spaks_length:
                    offset = distance_diff - self.sparks_target_new_spaks_length

                #print(f"Offset: {offset} - Target {self.sparks_target_appear_distance} - Diff {distance_diff}")               
                
                self.sparks_array[0][offset:sparks_fly_steps] =  sparks_maincolor[0]
                self.sparks_array[1][offset:sparks_fly_steps] =  sparks_maincolor[1]
                self.sparks_array[2][offset:sparks_fly_steps] =  sparks_maincolor[2]


        #output_array = firebase_array

        spars_array_cutted = np.zeros((3, led_count))
        spars_array_cutted[0][:self.sparks_area_current_length] = self.sparks_array[0][:self.sparks_area_current_length]
        spars_array_cutted[1][:self.sparks_area_current_length] = self.sparks_array[1][:self.sparks_area_current_length] 
        spars_array_cutted[2][:self.sparks_area_current_length] = self.sparks_array[2][:self.sparks_area_current_length] 

        mask_array = np.zeros((3, led_count))
        mask_array[0][:self.sparks_area_current_length] = 100
        mask_array[1][:self.sparks_area_current_length] = 100
        mask_array[2][:self.sparks_area_current_length] = 100

        mask_array[0][self.firebase_area_current_length-5:self.firebase_area_current_length+5] = 50
        mask_array[1][self.firebase_area_current_length-5:self.firebase_area_current_length+5] = 50
        mask_array[2][self.firebase_area_current_length-5:self.firebase_area_current_length+5] = 50

        mask_array[0][self.sparks_area_current_length-10:self.sparks_area_current_length+10] = 50
        mask_array[1][self.sparks_area_current_length-10:self.sparks_area_current_length+10] = 50
        mask_array[2][self.sparks_area_current_length-10:self.sparks_area_current_length+10] = 50

        mask_array = gaussian_filter1d(mask_array, sigma=mask_blur)

        overlay_array = np.where(spars_array_cutted != 0, spars_array_cutted, firebase_array)

        output_array = (output_array * mask_array) / 100

        output_array = gaussian_filter1d(overlay_array, sigma=blur)



        


        # Add the output array to the queue.
        self.queue_output_array_blocking(output_array)



    def get_current_length(self, current_length, steps, target_length):

        # Increase current length
        if current_length <= target_length:
            current_length = current_length + steps
            
            # If new current length is longer than the target, set the target length.
            if current_length > target_length:
                current_length = target_length
        else:
        # Decrease current length
            current_length = current_length - steps
            if current_length < target_length:
                current_length = target_length

        return current_length
    
