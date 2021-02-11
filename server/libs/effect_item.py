class EffectItem():
    def __init__(self, effect_enum, device_id):
        self.__effect_enum = effect_enum
        self.__device_id = device_id

    def get_effect_enum(self):
        return self.__effect_enum

    def get_device_id(self):
        return self.__device_id

    effect_enum = property(get_effect_enum)
    device_id = property(get_device_id)
