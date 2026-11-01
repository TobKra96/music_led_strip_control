# Release notes

## 3.0.0 (unreleased)

### System control

- The **System Status** page has a **Power** card to reboot or shut down the machine MLSC runs on, after a confirmation. The page follows the action until the machine is back: a reboot returns to the login page, a shutdown ends on a banner telling you to switch it on by hand.
- The card is disabled, with the reason shown, when MLSC is not on Linux, `systemctl` is missing or MLSC does not run as root (for example in a dev shell).
- The Power card warns when `mlsc.service` is not installed or not enabled, because MLSC would not start again after a reboot.
- A **Server logs** card shows the lines MLSC wrote during the current boot, read from the systemd journal.
- API: `GET /api/v2/system/power`, `POST /api/v2/system/reboot` and `/shutdown` (202, or the `PowerActionBlocked` problem), and `GET /api/v2/system/logs`.

### Gradients & Colours

- New **Gradients & Colours** page under Settings to create, edit, rename, duplicate and delete your own gradients and colours. Predefined entries are read-only; duplicate one to get an editable copy.
- Editing an entry that a running effect uses restarts only the Devices that use it.
- API: `/api/v2/gradients` and `/api/v2/colors` (see the OpenAPI docs for the `PredefinedEntryReadOnly`, `EntryInUse` and `RefreshFailed` problems).

### Upgrading: entries renamed to `(custom)`

Predefined names are now reserved. When an older config is migrated:

- A predefined gradient or colour you had edited is renamed `<name> (custom)` and the shipped version is restored.
- A custom entry whose name matches a predefined one (ignoring case) is renamed `<name> (custom)`.
- Effect settings that used the old name follow the rename, so nothing changes visually.

Every rename is listed in the Migration Report of the Config Migration. Check it after upgrading if you want to know which of your entries were renamed.
