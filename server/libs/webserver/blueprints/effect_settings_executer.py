from libs.webserver.executer_base import ExecuterBase, handle_config_errors


class EffectSettingsExecuter(ExecuterBase):

    # Return setting_value.
    @handle_config_errors
    def get_effect_setting(self, device, effect, setting_key):
        selected_device = device
        if device == self.all_devices_id:
            selected_device = next(iter(self._config["device_configs"]))

        return self._config["device_configs"][selected_device]["effects"][effect][setting_key]

    @handle_config_errors
    def get_effect_settings(self, device, effect):
        settings = dict()
        selected_device = device

        self.logger.debug(f"Get effect settings of {device}, Effect: {effect}")

        if device == self.all_devices_id:
            selected_device = next(iter(self._config["device_configs"]))
            self.logger.debug(f"Get effect settings of {selected_device}")

        for effect_setting_key in self._config["device_configs"][selected_device]["effects"][effect]:
            settings[effect_setting_key] = self._config["device_configs"][selected_device]["effects"][effect][effect_setting_key]

        self.logger.debug(f"Settings: {settings}")

        return settings

    def set_effect_setting(self, device, effect, settings):
        if device == self.all_devices_id:
            return self.set_effect_setting_for_all(effect, settings)

        for setting_key, setting_value in settings.items():
            self._config["device_configs"][device]["effects"][effect][setting_key] = setting_value
        self.update_cycle_job(device, effect)

        self.save_config()
        self.refresh_device(device)
        return self._config["device_configs"]

    def set_effect_setting_for_all(self, effect, settings):
        for device_key in self._config["device_configs"]:
            for setting_key, setting_value in settings.items():
                self._config["device_configs"][device_key]["effects"][effect][setting_key] = setting_value
            self.update_cycle_job(device_key, effect)

        self.save_config()
        self.refresh_device(self.all_devices_id)
        return self._config["device_configs"]

    def update_cycle_job(self, device, effect):
        """
        Change the Random Cycle Effect job interval on save.
        """
        if effect != "effect_random_cycle":
            return

        job = self.scheduler.get_job(device)
        if job:
            was_running = job.next_run_time
            interval = self._config["device_configs"][device]["effects"]["effect_random_cycle"]["interval"]
            self.scheduler.reschedule_job(device, trigger="interval", seconds=interval)
            if not was_running:  # Workaround flag because `reschedule_job()` unpauses jobs.
                self.scheduler.pause_job(device)
