from enum import Enum
class NotificationEnum(Enum):
    config_refresh = 1
    config_refresh_finished = 2
    config_refresh_failed = 3
    process_stop = 4
    process_pause = 5
    process_continue = 6
    