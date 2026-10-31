from __future__ import annotations

import copy

from mlsc.color_registry import CONFIG_KEYS, MAX_NAME_LENGTH, entry_errors, find_name, find_usages, name_errors, rename_usages
from mlsc.webserver.executer_base import ExecuterBase
from mlsc.webserver.messages import AlreadyExists, EntryInUse, EntryNotFound, PredefinedEntryReadOnly, ValidationError

DATA_FIELDS = {"colour": "rgb", "gradient": "stops"}


def _problem(message, detail=None, errors=None, usages=None):
    from mlsc.api.v2.errors import ProblemError  # Imported late: the api package imports the executers.

    return ProblemError(message, detail, errors, usages=usages)


class EntryExecuter(ExecuterBase):
    """Create, edit, rename, duplicate and delete the named colours and gradients of the config.

    The config is saved first; then the Devices that use the entry are restarted and the call waits for them.
    """

    def _entries(self, kind: str) -> dict:
        return self._config[CONFIG_KEYS[kind]]

    def _predefined(self, kind: str) -> set[str]:
        template = self._config_instance.load_template() or {}
        return {name.casefold() for name in template.get(CONFIG_KEYS[kind], {})}

    def _view(self, kind: str, name: str) -> dict:
        return {"name": name, DATA_FIELDS[kind]: copy.deepcopy(self._entries(kind)[name]), "predefined": name.casefold() in self._predefined(kind)}

    def _require(self, kind: str, name: str) -> str:
        """Return the stored spelling of `name`, or raise a 404."""
        stored = find_name(self._entries(kind), name)
        if stored is None:
            raise _problem(EntryNotFound, f"There is no {kind} named {name}.")
        return stored

    def _require_custom(self, kind: str, stored: str) -> None:
        if stored.casefold() in self._predefined(kind):
            raise _problem(PredefinedEntryReadOnly, f"{stored} is predefined.")

    def _require_valid(self, kind: str, name: str | None, data: object) -> None:
        errors = [{"field": "name", "detail": detail} for detail in (name_errors(name) if name is not None else [])]
        if data is not None:
            errors += [{"field": DATA_FIELDS[kind], "detail": detail} for detail in entry_errors(kind, data)]
        if errors:
            raise _problem(ValidationError, errors=errors)

    def _require_free(self, kind: str, name: str, own: str | None = None) -> None:
        taken = find_name(self._entries(kind), name)
        if taken is not None and taken != own:
            raise _problem(AlreadyExists, f"A {kind} named {taken} already exists.")

    def list_entries(self, kind: str) -> list[dict]:
        return [self._view(kind, name) for name in self._entries(kind)]

    def get_entry(self, kind: str, name: str) -> dict:
        return self._view(kind, self._require(kind, name))

    def get_usages(self, kind: str, name: str) -> list[dict]:
        return find_usages(self._config, kind, self._require(kind, name))

    def create_entry(self, kind: str, name: str, data: object) -> dict:
        self._require_valid(kind, name, data)
        self._require_free(kind, name)
        self._entries(kind)[name] = copy.deepcopy(data)
        return self._save_and_refresh(kind, name)

    def update_entry(self, kind: str, name: str, new_name: str | None, data: object) -> dict:
        stored = self._require(kind, name)
        self._require_custom(kind, stored)
        if new_name == stored:
            new_name = None
        self._require_valid(kind, new_name, data)
        if new_name is not None:
            self._require_free(kind, new_name, own=stored)
        entries = self._entries(kind)
        if data is not None:
            entries[stored] = copy.deepcopy(data)
        if new_name is not None:
            entries[new_name] = entries.pop(stored)
            rename_usages(self._config, kind, stored, new_name)
        return self._save_and_refresh(kind, new_name or stored)

    def delete_entry(self, kind: str, name: str) -> None:
        stored = self._require(kind, name)
        self._require_custom(kind, stored)
        usages = find_usages(self._config, kind, stored)
        if usages:
            raise _problem(EntryInUse, f"{stored} is used by {len(usages)} effect setting(s).", usages=usages)
        del self._entries(kind)[stored]
        self.save_config()

    def duplicate_entry(self, kind: str, name: str) -> dict:
        stored = self._require(kind, name)
        entries = self._entries(kind)
        number = 1
        while True:
            suffix = " (copy)" if number == 1 else f" (copy {number})"
            copy_name = stored[:MAX_NAME_LENGTH - len(suffix)].rstrip() + suffix
            if find_name(entries, copy_name) is None:
                break
            number += 1
        entries[copy_name] = copy.deepcopy(entries[stored])
        return self._save_and_refresh(kind, copy_name)

    def _save_and_refresh(self, kind: str, name: str) -> dict:
        self.save_config()
        self.refresh_devices_using(kind, name)
        return self._view(kind, name)
