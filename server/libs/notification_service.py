from libs.notification_enum import NotificationEnum # pylint: disable=E0611, E0401
from time import sleep

class NotificationService():
    def start(self, config_lock, notification_queue_output_in, notification_queue_output_out, notification_queue_effects_in, notification_queue_effects_out, notification_queue_webserver_in, notification_queue_webserver_out):
        self._config_lock = config_lock
        self._notification_queue_output_in = notification_queue_output_in
        self._notification_queue_output_out = notification_queue_output_out
        self._notification_queue_effects_in = notification_queue_effects_in
        self._notification_queue_effects_out = notification_queue_effects_out
        self._notification_queue_webserver_in = notification_queue_webserver_in
        self._notification_queue_webserver_out = notification_queue_webserver_out

        self._cancel_token = False
        print("NotificationService component started.")
        while not self._cancel_token:
            # 1. Check Webserver
            # 2. Check Output
            # 3. Check Effects
            sleep(0.5)

            if not self._notification_queue_webserver_out.empty():
                current_webserver_out = self._notification_queue_webserver_out.get()

                if current_webserver_out is NotificationEnum.config_refresh:
                    
                    print("Reload config..")
                    self.config_refresh()
                    print("Config reloaded.")
    
    
    
    def stop(self):
        self._cancel_token = True

    def config_refresh(self):
        # Summary
        # 1. Pause every process that have to refresh the config.
        # 2. Send the refresh command
        # 3. Wait for all to finish the process.
        # 4. Continue the processes.

        # 1. Pause every process that have to refresh the config.
        self._notification_queue_output_in.put(NotificationEnum.process_pause)
        self._notification_queue_effects_in.put(NotificationEnum.process_pause)

        # 2. Send the refresh command
        self._notification_queue_output_in.put(NotificationEnum.config_refresh)
        self._notification_queue_effects_in.put(NotificationEnum.config_refresh)

        # 3. Wait for all to finish the process.
        processes_not_ready = True

        output_ready = False
        effect_ready = False
        while processes_not_ready:

            # Check the notification queue of output, if it is ready to continue
            if(not self._notification_queue_output_out.empty()):
                current_output_out =  self._notification_queue_output_out.get()
                if current_output_out is NotificationEnum.config_refresh_finished:
                    output_ready = True

            # Check the notification queue of effects, if it is ready to continue
            if(not self._notification_queue_effects_out.empty()):
                current_effects_out =  self._notification_queue_effects_out.get()
                if current_effects_out is NotificationEnum.config_refresh_finished:
                    effect_ready = True

            if output_ready and effect_ready:
                processes_not_ready = False

        # 4. Continue the processes.
        self._notification_queue_output_in.put(NotificationEnum.process_continue)
        self._notification_queue_effects_in.put(NotificationEnum.process_continue)

