from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from libs.notification_item import NotificationItem # pylint: disable=E0611, E0401
from time import sleep

class NotificationService():
    def start(self, config_lock, notification_queue_device_manager_in, notification_queue_device_manager_out, notification_queue_audio_in, notification_queue_audio_out, notification_queue_webserver_in, notification_queue_webserver_out):
        self._config_lock = config_lock
        self._notification_queue_device_manager_in = notification_queue_device_manager_in
        self._notification_queue_device_manager_out = notification_queue_device_manager_out
        self._notification_queue_audio_in = notification_queue_audio_in
        self._notification_queue_audio_out = notification_queue_audio_out
        self._notification_queue_webserver_in = notification_queue_webserver_in
        self._notification_queue_webserver_out = notification_queue_webserver_out

        self._current_notification_item = NotificationItem(NotificationEnum.config_refresh, "all_devices")

        self._cancel_token = False
        print("NotificationService component started.")
        while not self._cancel_token:
            # 1. Check Webserver
            # 2. Check Output
            # 3. Check Effects
            sleep(0.5)

            if not self._notification_queue_webserver_out.empty():
                print("NotificationService: New Notification detected.")
                self._current_notification_item = self._notification_queue_webserver_out.get()

                if self._current_notification_item.notification_enum is NotificationEnum.config_refresh:
                    
                    print("Reload config..")
                    self.config_refresh(self._current_notification_item)
                    print("Config reloaded.")
    
    
    
    def stop(self):
        self._cancel_token = True

    def config_refresh(self, original_notification_item):

        device_id = original_notification_item.device_id

        # Summary
        # 1. Pause every process that have to refresh the config.
        # 2. Send the refresh command
        # 3. Wait for all to finish the process.
        # 4. Continue the processes.

        # 1. Pause every process that have to refresh the config.
        self._notification_queue_device_manager_in.put(NotificationItem(NotificationEnum.process_pause, device_id))
        self._notification_queue_audio_in.put(NotificationItem(NotificationEnum.process_pause, device_id))

        # 2. Send the refresh command
        self._notification_queue_device_manager_in.put(NotificationItem(NotificationEnum.config_refresh, device_id))
        self._notification_queue_audio_in.put(NotificationItem(NotificationEnum.config_refresh, device_id))

        # 3. Wait for all to finish the process.
        processes_not_ready = True

        device_ready = False
        effect_ready = False
        while processes_not_ready:

            # Check the notification queue of device_manager, if it is ready to continue
            if(not self._notification_queue_device_manager_out.empty()):
                current_output_out =  self._notification_queue_device_manager_out.get()
                if current_output_out.notification_enum is NotificationEnum.config_refresh_finished:
                    device_ready = True
                    print("Device refreshed the config.")

            # Check the notification queue of audio, if it is ready to continue
            if(not self._notification_queue_audio_out.empty()):
                current_effects_out =  self._notification_queue_audio_out.get()
                if current_effects_out.notification_enum is NotificationEnum.config_refresh_finished:
                    effect_ready = True
                    print("Audio refreshed the config.")

            if device_ready and effect_ready:
                processes_not_ready = False

        # 4. Continue the processes.
        self._notification_queue_device_manager_in.put(NotificationItem(NotificationEnum.process_continue, device_id))
        self._notification_queue_audio_in.put(NotificationItem(NotificationEnum.process_continue, device_id))

