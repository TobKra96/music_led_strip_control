"""Rules and bookkeeping for the named colours and gradients in the config.

The registry says which effect settings hold a Colour or a Gradient. It is derived from the effect settings schema, so the usage scan,
the rename rewrite and the config validator cannot drift apart.
"""
import re
from functools import cache

from mlsc.webserver.schemas.config_validator_service import color_enum, effect_schema, gradient_enum
from mlsc.webserver.schemas.custom_types import MAX_ENTRY_NAME_LENGTH, MAX_GRADIENT_STOPS, MIN_GRADIENT_STOPS, valid_entry_name

COLOUR = "colour"
GRADIENT = "gradient"

CONFIG_KEYS = {COLOUR: "colors", GRADIENT: "gradients"}
""" The config section that holds the entries of each kind. """

FALLBACK_NAMES = {COLOUR: "red", GRADIENT: "spectral"}
""" What an effect renders when the entry it references does not exist (a Missing Reference). """

MAX_NAME_LENGTH = MAX_ENTRY_NAME_LENGTH
MIN_STOPS = MIN_GRADIENT_STOPS
MAX_STOPS = MAX_GRADIENT_STOPS

_NAME_RE = re.compile(valid_entry_name)


def name_errors(name: object) -> list[str]:
    if not isinstance(name, str):
        return ["The name must be text."]
    if not name.strip():
        return ["The name must not be empty."]
    if len(name) > MAX_NAME_LENGTH:
        return [f"The name must be at most {MAX_NAME_LENGTH} characters."]
    if not _NAME_RE.match(name):
        return ["The name may only contain letters, digits, spaces, dashes and underscores, and must not start or end with a space."]
    return []


def find_name(names, name: str) -> str | None:
    """Return the stored spelling of `name`, compared case-insensitively, or `None`."""
    folded = name.casefold()
    return next((stored for stored in names if stored.casefold() == folded), None)


def _rgb_errors(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(channel, int) and not isinstance(channel, bool) for channel in value):
        return ["A colour must be three whole numbers [r, g, b]."]
    if not all(0 <= channel <= 255 for channel in value):
        return ["Each colour channel must be between 0 and 255."]
    return []


def entry_errors(kind: str, value: object) -> list[str]:
    """Return a message per problem with the data of a colour (`[r, g, b]`) or gradient (a list of such stops)."""
    if kind == COLOUR:
        return _rgb_errors(value)
    if not isinstance(value, list) or not MIN_STOPS <= len(value) <= MAX_STOPS:
        return [f"A gradient needs between {MIN_STOPS} and {MAX_STOPS} stops."]
    return [error for stop in value for error in _rgb_errors(stop)]


@cache
def registry() -> dict[str, dict[str, str]]:
    """Return `{effect: {setting: kind}}` for every effect setting that holds a Colour or a Gradient."""
    kinds = {id(color_enum): COLOUR, id(gradient_enum): GRADIENT}
    found = {}
    for effect, effect_properties in effect_schema["properties"].items():
        if "properties" not in effect_properties:
            continue
        settings = {setting: kinds[id(prop["enum"])] for setting, prop in effect_properties["properties"].items() if id(prop.get("enum")) in kinds}
        if settings:
            found[effect] = settings
    return found


def _references(config: dict, kind: str, name: str):
    """Yield `(target, effect, setting, settings)` for every setting of every Device that holds `name`."""
    for target, device in config["device_configs"].items():
        for effect, settings in registry().items():
            stored = device["effects"].get(effect, {})
            for setting, setting_kind in settings.items():
                if setting_kind == kind and stored.get(setting) == name:
                    yield target, effect, setting, stored


def find_usages(config: dict, kind: str, name: str) -> list[dict[str, str]]:
    """Return where the entry is used, as `{target, effect, setting}`. Every effect counts, active or not."""
    return [{"target": target, "effect": effect, "setting": setting} for target, effect, setting, _ in _references(config, kind, name)]


def rename_usages(config: dict, kind: str, old: str, new: str) -> list[dict[str, str]]:
    """Point every usage of `old` at `new` and return the rewritten usages."""
    rewritten = []
    for target, effect, setting, stored in list(_references(config, kind, old)):
        stored[setting] = new
        rewritten.append({"target": target, "effect": effect, "setting": setting})
    return rewritten
