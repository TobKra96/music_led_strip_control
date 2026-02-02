class NotificationItem:
    def __init__(self, notification_enum, device_id) -> None:
        self.__notification_enum = notification_enum
        self.__device_id = device_id

    def get_notification_enum(self):
        return self.__notification_enum

    def get_device_id(self):
        return self.__device_id

    notification_enum = property(get_notification_enum)
    device_id = property(get_device_id)
