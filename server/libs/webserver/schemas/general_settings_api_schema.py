from libs.webserver.schemas.config_validator_service import general_settings_schema, remove_required_keys

_GENERAL_SETTINGS_SCHEMA_PARSED = remove_required_keys(general_settings_schema)
""" Parsed general settings schema. Using schema from config validator service to avoid duplication. """

ONE_GENERAL_SETTING_SCHEMA = {
    "type": "object",
    "required": ["setting_key"],
    "properties": {
        "setting_key": {
            "type": "string",
            "enum": [
                "default_sample_rate",
                "device_groups",
                "device_id",
                "frames_per_buffer",
                "log_file_enabled",
                "log_level_console",
                "log_level_file",
                "max_frequency",
                "min_frequency",
                "min_volume_threshold",
                "n_fft_bins",
                "n_rolling_history",
                "webserver_port",
            ]
        },
    },
}
""" Schema for `GET /api/settings/general` with `setting_key` as a query parameter. """


_GENERAL_SETTINGS_PROPS = _GENERAL_SETTINGS_SCHEMA_PARSED["properties"]
SET_GENERAL_SETTINGS_SCHEMA = {
    "type": "object",
    "required": ["settings"],
    "properties": {
        "settings": {
            "type": "object",
            "properties": _GENERAL_SETTINGS_PROPS,
            "additionalProperties": False,
        },
    },
}
""" Schema for `POST /api/settings/general`. """
