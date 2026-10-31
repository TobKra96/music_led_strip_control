# Reboot, shutdown and journal access from the MLSC service (ticket #334)

Research date: 2026-10-31. Planning only; no project code changed.
Sources are primary only: systemd man pages (freedesktop.org, "latest" unless a tag is named), systemd source (GitHub `systemd/systemd`, tag `v252` = Debian Bookworm's version, see caveat), Debian's systemd packaging (Salsa), and the Raspberry Pi OS image builder (`RPi-Distro/pi-gen`). Each claim names its source in brackets. Anything not verified from a primary source is marked **UNVERIFIED**.

## Question

On Raspberry Pi OS (Bookworm) with the unit MLSC installs (`User=root`, `NoNewPrivileges=true`, `ProtectHome=read-only`, `ReadWritePaths`), do `systemctl reboot` / `systemctl poweroff` and `journalctl -u mlsc` work from the service process? Is the journal persistent or volatile by default? Which `journalctl` options give a bounded, filterable, JSON tail by priority and text?

## Short answer

- **Reboot and shutdown should work as-is.** The unit has no option that blocks them: `NoNewPrivileges=` only stops privilege gain through `execve()`, and a root process does not need to gain any [systemd.exec]. `ProtectHome=read-only` only touches `/home`, `/root`, `/run/user` [systemd.exec]. Running `systemctl reboot` / `poweroff` as root goes to logind over D-Bus, with no polkit prompt needed for root in practice. **Not run on a Pi in this research**; the reasoning is from docs and source only (see "Verify on a Pi").
- **Where the unit lives.** `master` has no hardened unit (`setup.sh` writes a plain `User=root` unit). The hardened unit is `render_unit()` in `src/mlsc/service.py` on `dev_3.0` (commit a7cb821, #267). The check here uses that one: `User=root`, `ProtectHome=read-only`, `ReadWritePaths=<config dir>`, `NoNewPrivileges=true`. It sets **no** `ProtectSystem=`, `PrivateDevices=`, `PrivateNetwork=`, `RestrictAddressFamilies=` or `CapabilityBoundingSet=`.
- **Raspberry Pi OS (Bookworm) images ship a volatile journal.** pi-gen's `bookworm` branch sets `Storage=volatile` in `/etc/systemd/journald.conf` [pi-gen]. Logs live in `/run/log/journal` (RAM) and are **gone after every reboot**. So after a UI-triggered reboot the viewer will not show what happened before it, unless the user changes the setting.
- **`journalctl` can give a bounded, filtered JSON tail** with `-u mlsc -n N -p LEVEL -g REGEX -o json --no-pager`. Details below.
- **Root suffices to read the journal.** No `systemd-journal` group is needed for `User=root`.

## 1. Can the service run `systemctl reboot` / `poweroff`?

| Fact | Source |
| --- | --- |
| `systemctl reboot` and `poweroff` are "mostly equivalent to `systemctl start reboot.target` / `poweroff.target --job-mode=replace-irreversibly --no-block`, but also print a wall message". They are asynchronous: they return once the operation is enqueued, not when done. | https://www.freedesktop.org/software/systemd/man/latest/systemctl.html |
| `--no-wall`, `--message=`, `--when=` (with `cancel`), `--force` exist. `--force` skips orderly shutdown of units (once) or skips even the manager (twice). A normal UI action should not use `--force`. | same |
| `poweroff` powers the machine off; `halt` "will simply halt the OS kernel after shutting down, leaving the hardware powered on". Use `poweroff` for "shutdown". | same |
| Without `--force`, `systemctl reboot` / `poweroff` first calls logind (`org.freedesktop.login1` `Reboot` / `PowerOff`) "to allow authentication with polkit". If that returns `-EACCES`, `-EOPNOTSUPP` or `-EINPROGRESS` it fails with that error; any other error falls back to starting the target through the manager. | https://raw.githubusercontent.com/systemd/systemd/v252/src/systemctl/systemctl-start-special.c |
| Before that it runs `logind_check_inhibitors`. That check returns early when `--force` is given, when `--when=` is set, and (when `--check-inhibitors` is unset) when `geteuid() == 0` or stdin is not a TTY. So inhibitors never block the service. | https://raw.githubusercontent.com/systemd/systemd/v252/src/systemctl/systemctl-logind.c |
| For `geteuid() == 0`, `systemctl` connects to `unix:path=/run/systemd/private` and falls back to the system bus on failure. A non-root caller goes to the system bus. | https://raw.githubusercontent.com/systemd/systemd/v252/src/shared/bus-util.c |
| logind is documented as providing "polkit-based access for users for operations such as system shutdown". The page does not name the polkit actions. | https://www.freedesktop.org/software/systemd/man/latest/systemd-logind.service.html |

Sandboxing, option by option (the first four are what MLSC sets):

- **`NoNewPrivileges=true`**: "ensures that the service process and all its children can never gain new privileges through `execve()`" [systemd.exec]. The process is already root, so there is nothing to gain. It would matter only for `sudo`/setuid helpers (a non-root service user calling `sudo systemctl reboot` would break), which is not MLSC's setup.
- **`ProtectHome=read-only`**: "`/home/`, `/root`, and `/run/user` are made inaccessible and empty" for `true`, read-only for `read-only` [systemd.exec]. `/run/systemd/private`, `/run/dbus/system_bus_socket` are not under those paths.
- **`ReadWritePaths=`**: allow-lists write access only; adds nothing against reboot. The man page notes `/run/` "needs to be writable for setting up mount namespace and propagation" [systemd.exec].
- **Read-only mounts do not block D-Bus.** The man page states the read-only/inaccessible path options "do not affect the ability for programs to connect to and communicate with AF_UNIX sockets in these directories" and "cannot be used to lock down access to IPC services" [systemd.exec]. So `ProtectSystem=` would not block D-Bus connect either.
- **Options MLSC does not set but a future hardening pass might**, and what they would do [systemd.exec]:
  - `PrivateNetwork=true`: new network namespace with only `lo`. Cuts the web UI off the LAN, so it is not an option for MLSC anyway.
  - `RestrictAddressFamilies=`: if it excludes `AF_UNIX` the service cannot reach `/run/systemd/private` or the system bus. Keep `AF_UNIX` (MLSC also needs `AF_INET`/`AF_INET6` for the web server).
  - `PrivateDevices=true`: a new `/dev` with API pseudo devices only. Irrelevant to reboot, but would remove `/dev/mem`, which `rpi_ws281x` needs (the reason for `User=root`, per the comment in `render_unit`). Do not add.
  - `ProtectKernelLogs=true`: denies the kernel ring buffer and drops `CAP_SYSLOG`. Does not affect reboot.
  - `SystemCallFilter=` with the `@reboot` group: "System calls for rebooting and reboot preparation" (e.g. `reboot(2)`, `kexec`). Only relevant for `systemctl --force --force`, which calls `reboot(2)` from the `systemctl` process itself [systemctl man page, `halt`]. A normal reboot is done by PID 1, not by the service's process.
  - `CapabilityBoundingSet=` / `PrivateUsers=`: a user namespace or dropped caps can break privileged calls. **UNVERIFIED** here for D-Bus-based reboot (the relevant man page text was not read). Not set by MLSC.
- **Needs a running system D-Bus and logind.** `systemctl reboot` tries logind first (above), then falls back to PID 1 on non-permission errors. On a full Pi OS image both are present. **UNVERIFIED** for Pi OS Lite whether `dbus` is always installed; check `ls /run/dbus/system_bus_socket` on a Lite image. If logind is unreachable, the v252 code falls through to starting the target via the manager for errors other than the three "no fallback" codes (reading of source, not tested).
- **Version caveat.** Source was read at tag `v252` (Debian Bookworm ships systemd 252; **the version number on the image was not checked**). Man pages are "latest" and may describe newer behaviour (e.g. `--when=`, `--check-inhibitors`). The `v252` code path was the one quoted.

## 2. Is the journal persistent?

- **systemd default.** `Storage=` takes `volatile`, `persistent`, `auto`, `none`. "`auto` behaves like `persistent` if the `/var/log/journal` directory exists, and `volatile` otherwise" [journald.conf: https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html].
- **Debian.** Debian's `systemd.postinst` creates `/var/log/journal` on new installs ("Enable persistent journal, in auto-mode, by default on new installs") [https://salsa.debian.org/systemd-team/systemd/-/raw/debian/master/debian/systemd.postinst]. So stock Debian is persistent.
- **Raspberry Pi OS overrides that.** `stage2/01-sys-tweaks/01-run.sh` on the `bookworm` branch runs `sed -i 's/^#\?Storage=.*/Storage=volatile/' "${ROOTFS_DIR}/etc/systemd/journald.conf"`, from commit 13c185c "Switch default journald storage to volatile" (2024-11-19), [https://github.com/RPi-Distro/pi-gen/blob/bookworm/stage2/01-sys-tweaks/01-run.sh, commit https://github.com/RPi-Distro/pi-gen/commit/13c185cb7946efd667f6a516d2a493f24a9542a2]. `bookworm` branch HEAD was dated 2026-10-06 at query time.
- **Caveats.**
  - The commit date means **images built before 2024-11-19 may differ** (and may be persistent). **UNVERIFIED** which image releases contain it; the Raspberry Pi docs page for the OS (https://www.raspberrypi.com/documentation/computers/os.html) says nothing about the journal.
  - pi-gen's `master` branch version of that script has no journal line. **UNVERIFIED** which branch builds the current official images (Bookworm vs Trixie, 32/64-bit). Check `grep Storage /etc/systemd/journald.conf` on the target.
  - Users can flip it by setting `Storage=persistent` (or creating `/var/log/journal`). Reading the `Storage=` value on the host is a cheap way for the UI to know whether history survives a reboot.
- **Size.** `RuntimeMaxUse=` / `SystemMaxUse=` default to 10% of the filesystem, `KeepFree=` to 15%, each calculated value capped at 4G [journald.conf]. On a volatile journal that is RAM-backed `/run`, so old entries rotate out on a busy system; a `-n` tail is still fine.
- **Consequence for the page.** The viewer shows "this boot" only on stock Pi OS images. Reboot from the UI then clears the log. Options for the spec: show a note when `Storage=volatile`, or document how to make it persistent. Out of scope for this ticket to decide.

## 3. `journalctl` options for a bounded, filtered, machine-readable tail

All from https://www.freedesktop.org/software/systemd/man/latest/journalctl.html unless noted.

| Need | Option | Notes |
| --- | --- | --- |
| Only the `mlsc` unit | `-u mlsc` (`--unit=`) | Repeatable. Matches the unit and units it spawns. |
| Last N entries | `-n N` (`--lines=`) | "positive integer or `all`"; default 10 if given without value. `-n` implies nothing about order: output is oldest-first within the N. |
| Newest first | `-r` (`--reverse`) | Optional. |
| Priority | `-p LEVEL` or `-p FROM..TO` | Numeric or names (`err`, `warning`, ...). "A single level also includes all more important levels." Range includes both ends. So `-p warning` = emerg..warning; `-p err..warning` = err, warning. |
| Text filter | `-g REGEX` (`--grep=`) | Matches the `MESSAGE=` field only. PCRE2. "If the pattern is all lowercase, matching is case insensitive" (override with `--case-sensitive=yes`). Filter and limit combine: `-n` applies to entries after all filters (**UNVERIFIED** from this page; the order of `-g` vs `-n` was not stated. Test on a Pi). |
| JSON output | `-o json` | One JSON object per line ("separated by newline characters"). `-o json-pretty` is multi-line (not wanted). |
| No pager | `--no-pager` | Needed when stdout is not a TTY? Pager is not started for a pipe, but the flag is harmless and explicit. |
| Time window | `-S/--since`, `-U/--until` | `"2012-10-30 18:17:16"`, `yesterday`, `today`, `now`, relative `-1h`. Omitted time means 00:00:00. |
| Resume point | `--show-cursor`, `--after-cursor=C`, `-c/--cursor=C` | `--show-cursor` prints the cursor "after two dashes" after the last entry (in plain output; in JSON each entry carries `__CURSOR`). Format is private and may change. A cursor-based "give me what is new" poll is possible, no live tail needed. |
| Trim fields | `--output-fields=A,B` | Only affects verbose/export/JSON. `__CURSOR`, `__REALTIME_TIMESTAMP`, `__MONOTONIC_TIMESTAMP`, `_BOOT_ID` are always included. Useful: `MESSAGE,PRIORITY,SYSLOG_IDENTIFIER,_PID`. |
| This boot only | `-b` (`--boot`) | Not read from the page above. **UNVERIFIED** here. With a volatile journal it is all there is anyway. |
| Quiet when inaccessible | `-q` | Suppresses the warning about inaccessible system journals when run as a normal user. |

A suitable command for the viewer, built from the options above (not run in this research):

`journalctl -u mlsc -n 200 -p warning -g 'timeout' -o json --no-pager --output-fields=MESSAGE,PRIORITY,SYSLOG_IDENTIFIER`

JSON caveats from the same page:

- Values are JSON strings by default. Fields larger than 4096 bytes become `null` unless `--all` is passed. A repeated field becomes an array of values. Fields with non-printable or non-UTF8 bytes become **arrays of unsigned byte numbers**. Parsers must tolerate `MESSAGE` being a string, `null` or a number array.
- `PRIORITY` is a string of a digit in the JSON output (**UNVERIFIED** from this page, which does not show a sample entry; confirm on a Pi).
- Exit status: 0 on success, non-zero otherwise; the page does not say which code means "no entries" or "no access". **UNVERIFIED**. Do not rely on a specific code; parse stderr/empty output instead.
- Whether the Python `logging` output of MLSC lands in the journal with a useful `PRIORITY` depends on how stdout/stderr are mapped. `systemd.exec` sets stdout/stderr to the journal by default; the page text read here was truncated before `StandardOutput=`, so this is **UNVERIFIED**. Plain stdout lines get a default priority unless they carry `<N>` prefixes (`SyslogLevelPrefix=`; **UNVERIFIED**). Without prefixes, `-p` filtering will not separate WARNING from INFO. A decision for the spec: log through the journal API or add level prefixes.

## 4. Which user can read the journal?

- "By default, only root and users who are members of a few special groups are granted access to the system journal": **`systemd-journal`, `adm`, `wheel`** can read all journal files [journalctl man page, "Read access"].
- Files are `root:systemd-journal`, system journal mode `0640`, with additional read ACLs for `adm` and `wheel` where those groups exist [systemd `tmpfiles.d/systemd.conf.in`: https://raw.githubusercontent.com/systemd/systemd/main/tmpfiles.d/systemd.conf.in]. The same file sets `/run/log/journal` to `root:systemd-journal` with mode `2755`/`2750` (volatile case).
- **MLSC runs as `User=root`, so no group membership is needed.** If a later version drops root (the unit comment says `rpi_ws281x` needs `/dev/mem`), the service user would need `SupplementaryGroups=systemd-journal` in the unit (**the directive name is from general systemd knowledge, not read on a page here: UNVERIFIED**) or be in `adm`.
- Sandboxing: `ProtectSystem=` / `ProtectHome=` do not hide `/var/log/journal` or `/run/log/journal`. `ProtectSystem=strict` only makes them read-only [systemd.exec], which is enough for reading. `PrivateDevices=` and `ProtectKernelLogs=` do not affect journal files.
- `journalctl` is a client that opens the journal files directly (no daemon, no D-Bus), so it does not depend on the D-Bus access discussed in section 1. The `--user` journal is not relevant; MLSC is a system unit.

## Verify on a Pi (not done here)

These could not be checked without a device; each is a one-liner for a manual checklist:

1. Run `systemctl reboot` from inside the service's sandbox, for example with `systemd-run --pty -p User=root -p NoNewPrivileges=yes -p ProtectHome=read-only systemctl reboot` (the exact flags are a suggestion, **UNVERIFIED**), and confirm the machine reboots.
2. `grep -r Storage /etc/systemd/journald.conf /etc/systemd/journald.conf.d; ls /var/log/journal /run/log/journal; journalctl --disk-usage`.
3. `ls /run/dbus/system_bus_socket` on a Lite image; `systemctl --version`.
4. `journalctl -u mlsc -n 5 -p warning -g x -o json --no-pager | head -c 600` and compare `PRIORITY` type and whether `-n` applies after `-g`.

## Findings for the spec (#333 tickets #335, #336)

1. Use `systemctl reboot` and `systemctl poweroff` (not `halt`) with no `--force`. They return as soon as the job is queued, so the API should answer first and the browser should expect the connection to drop.
2. The hardened unit needs no change for reboot/shutdown. Keep `AF_UNIX` allowed if sandboxing is ever tightened.
3. Treat the journal as "this boot only" unless the host reports persistent storage.
4. Log tail command above covers N, level, text, JSON, with `--after-cursor` available for incremental refresh. Parsers must handle `null` and byte-array `MESSAGE` values.
5. Remaining unknowns are listed under "Verify on a Pi" and the **UNVERIFIED** marks.
