# Can the hardened service reboot the machine and read its journal? (#334)

Part of #333. Sources: systemd man pages on freedesktop.org (`latest`), fetched 2026-10-31. Nothing here was run on a Pi; items marked **Unverified** need a check on hardware (see the end).

## Answer

- **Reboot / poweroff: yes, expected to work.** The unit runs as `root` with no `CapabilityBoundingSet=` and no `ProtectKernel*`/`PrivateDevices=`. `NoNewPrivileges=true`, `ProtectHome=read-only` and `ReadWritePaths` limit the unit's own processes (privilege gain, filesystem view). They are not documented to block talking to systemd. `systemctl reboot` only enqueues `reboot.target` over the system manager's IPC.
- **`journalctl -u mlsc`: yes, expected to work.** Root can read all journal files. The journal lives in `/var/log` or `/run/log`, which are outside what `ProtectHome=` hides, and `journalctl` only reads them.
- **Persistence: depends on `/var/log/journal`.** Default is `Storage=auto`: persistent if `/var/log/journal` exists, otherwise volatile (RAM, lost on reboot). Whether Bookworm images create that directory is **Unverified** (Raspberry Pi docs are silent).
- **Bounded, filterable, JSON tail:** `journalctl -u mlsc -o json --no-pager -n 200 -p warning..emerg -g 'pattern'`.

## Evidence

### Service hardening vs `systemctl reboot` / `poweroff`

The unit is generated in `src/mlsc/service.py` (`User=root`, `ProtectHome=read-only`, `ReadWritePaths={config_dir}`, `NoNewPrivileges=true`).

- systemctl: `reboot` is "mostly equivalent to `systemctl start reboot.target --job-mode=replace-irreversibly --no-block`" plus a wall message; `poweroff` likewise with `poweroff.target`. Both return without waiting. Source: <https://www.freedesktop.org/software/systemd/man/latest/systemctl.html>
- `--force` (once) skips the orderly unit shutdown; twice, "the system manager is not contacted". Not needed normally.
- systemd.exec: `NoNewPrivileges=` "only has an effect on the unit's processes themselves" and "no effect on processes potentially invoked on request of them". The read-only/inaccessible path options "cannot be used to lock down access to IPC services", and "the effect of these settings may be undone by privileged processes". `ProtectHome=` "cannot ensure protection in all cases". Without `CapabilityBoundingSet=` the bounding set is unmodified. Source: <https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html>
- Inference: the reboot request is made over the system manager's IPC (D-Bus/private socket), which these options do not close, and root needs no polkit approval. systemd's page says nothing about who is authorised (the systemctl excerpt read had no polkit text), so this part is an inference. Caveat: the services' own filesystem view is restricted, so use absolute `/usr/bin/systemctl` or `shutil.which` at startup, not a config-dir path.
- The service is `KillMode=control-group`; a reboot kills it as part of shutdown. The HTTP response must be sent before, or the command run detached. `--no-block` already returns immediately.

### Journal access

- `journalctl`: "Members of the groups systemd-journal, adm, and wheel can read all journal files." Root qualifies. A non-root user would get only their own journals, plus a warning that `-q` hides. Source: <https://www.freedesktop.org/software/systemd/man/latest/journalctl.html>
- Hardening does not hide `/var/log/journal` or `/run/log/journal`. `ProtectHome=read-only` only concerns `/home`, `/root`, `/run/user`. (ProtectHome semantics from systemd.exec; the specific list was not re-quoted from the page.)

### Persistent vs volatile

- journald.conf `Storage=`: values `volatile`, `persistent`, `auto`, `none`. "`auto` behaves like `persistent` if the `/var/log/journal` directory exists, and `volatile` otherwise." The compiled-in default is `auto` (the page's "persistent" wording applies to the namespace default value as built). Volatile data lives in `/run/log/journal`. Source: <https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html>
- Size caps: `SystemMaxUse=` and `RuntimeMaxUse=` default to 10% of the file system, capped at 4G (the `KeepFree=` pair uses 15%). On a small SD card, the cap is the lever to set explicitly.
- **Unverified:** Raspberry Pi OS Bookworm's default. <https://www.raspberrypi.com/documentation/computers/os.html> has nothing on journald, rsyslog or `/var/log/journal`. Check on a device with `ls -d /var/log/journal` and `journalctl --disk-usage`; `journalctl --list-boots` shows more than one boot only if it is persistent. If volatile, the fix is `mkdir -p /var/log/journal && systemd-tmpfiles --create --prefix /var/log/journal` and a restart of `systemd-journald`, or `Storage=persistent` in a drop-in.

### Options for a bounded, filterable, JSON tail

All from the journalctl page above.

| Need | Option |
| --- | --- |
| Only this service | `-u mlsc` (`--unit`) |
| Bound the size | `-n N` (most recent N, "positive integer or all", default 10) |
| Priority filter | `-p warning` (that level and more severe) or `-p err..emerg`; ranges include both ends. Levels 0 emerg to 7 debug |
| Text filter | `-g REGEX` (PCRE). All-lowercase pattern is case insensitive unless `--case-sensitive`. `-g` with `-n` (no `+`) implies `--reverse` |
| Time bound | `--since`, `--until` |
| This boot only | `-b` |
| Machine-readable | `-o json` (one object per line); `json-seq` adds 0x1E prefixes; `json-pretty` is multi-line |
| Trim fields | `--output-fields=PRIORITY,MESSAGE,__REALTIME_TIMESTAMP` (some fields are always printed) |
| No pager | `--no-pager` |
| Newest first | `-r` / `--reverse` |

Field meaning (<https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html>): `PRIORITY` is a decimal string "between 0 (emerg) and 7 (debug)" (so a string in JSON, not a number); `MESSAGE` is the human-readable text.

Suggested invocation (argv list, no shell):

```
journalctl -u mlsc -o json --no-pager -n 200 -p warning -g <regex> --output-fields=PRIORITY,MESSAGE,SYSLOG_IDENTIFIER
```

Notes for the implementer:
- Parse stdout line by line with `json.loads`. Non-UTF-8 or binary messages may appear as arrays of byte values instead of strings in JSON output (documented in the journal JSON format spec, not re-checked here).
- Pass the user's text through `-g` as one argv element (not a shell string). Invalid regexes make journalctl exit non-zero; surface that as a 400.
- `-g` combined with `-n` reverses order; sort by `__REALTIME_TIMESTAMP` yourself to be explicit.
- Apply a subprocess timeout and a hard cap on `-n`.

## Checks to run on a Pi (not done)

1. As the running service (or `sudo systemd-run` with the same properties): `systemctl reboot --no-block` works (use a test device).
2. `journalctl -u mlsc -o json -n 5 --no-pager` returns JSON from inside the service.
3. `ls -d /var/log/journal`, `journalctl --list-boots`, `journalctl --disk-usage`.
