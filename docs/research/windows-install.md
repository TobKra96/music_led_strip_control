# Research: Windows one-line install and autostart for MLSC

Resolves #347 (child of map #346). Facts only, from primary sources, retrieved 2026-11-09.
Items marked **UNVERIFIED** had no primary source reachable and must not be relied on.

## 1. `irm ... | iex` then `uv tool install music-led-strip-control`

### Installer command and execution policy
- The uv docs give the Windows command as `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`. [uv install docs](https://docs.astral.sh/uv/getting-started/installation/)
- `https://astral.sh/uv/install.ps1` answers 301 to `https://releases.astral.sh/installers/uv/latest/uv-installer.ps1` (checked with curl; `irm` follows redirects).
- The script itself refuses to run unless the execution policy is `Unrestricted`, `RemoteSigned` or `Bypass`, and prints `Set-ExecutionPolicy RemoteSigned -scope CurrentUser` as the fix. It also requires PowerShell 5+ and TLS 1.2. [installer source, 0.13.7](https://astral.sh/uv/install.ps1)
- So a machine whose policy is `Restricted` or `AllSigned` fails with that message even through `iex`; the `-ExecutionPolicy ByPass` form of the command avoids it. (Derived from the installer source above.)

### Install location and PATH
- uv installs to the first of `$env:XDG_BIN_HOME`, `$env:XDG_DATA_HOME/../bin`, `$HOME/.local/bin` (i.e. `%USERPROFILE%\.local\bin`). `UV_INSTALL_DIR` overrides it. [installer source](https://astral.sh/uv/install.ps1), [env vars](https://docs.astral.sh/uv/reference/environment/)
- It adds that dir to the **user** PATH by editing `HKCU\Environment\Path` (REG_EXPAND_SZ) and broadcasts a settings change via a dummy `[Environment]::SetEnvironmentVariable(..., 'User')`. No admin needed. [installer source](https://astral.sh/uv/install.ps1)
- It does **not** update the running session. It prints: restart the shell or run `$env:Path = "<dir>;$env:Path"`. So a one-liner that continues in the same session must refresh PATH itself, or call `uv` by absolute path. [installer source](https://astral.sh/uv/install.ps1)
- `UV_NO_MODIFY_PATH=1` disables the PATH edit. [env vars](https://docs.astral.sh/uv/reference/environment/)

### Tool executables
- `uv tool install` copies (Windows) the package's entry points into the executable directory; the directory must be on PATH, else uv warns; `uv tool update-shell` adds it. Executables of dependencies are not installed. [uv tools](https://docs.astral.sh/uv/concepts/tools/)
- Windows executable directory: `%XDG_BIN_HOME%`, else `%XDG_DATA_HOME%\..\bin`, else `%USERPROFILE%\.local\bin` (same place as uv). Tools live in `%APPDATA%\uv\data\tools`; uv-managed Pythons in `%APPDATA%\uv\data\python`. [uv storage](https://docs.astral.sh/uv/reference/storage/)
- So the entry point is `%USERPROFILE%\.local\bin\mlsc.exe` (default setup). A tool env is bound to one Python; if that Python is uninstalled the tool breaks. Tool installs ignore `.python-version` files; use `--python` to choose. [uv tools](https://docs.astral.sh/uv/concepts/tools/)

### Does uv fetch Python 3.11+ itself?
- "By default, uv will automatically download Python versions if they cannot be found on the system"; `python-downloads` is `automatic` by default, `manual` restricts downloads to `uv python install`. [uv Python versions](https://docs.astral.sh/uv/concepts/python-versions/)
- The docs read do not state explicitly that `uv tool install` obeys this. The general rule is documented; the tool-specific path is **UNVERIFIED** (needs a clean-VM test). Package metadata: `requires-python = ">=3.11"` (`pyproject.toml`).

### Wheel availability (PyPI JSON API, latest releases on 2026-11-09)
| Dependency | Latest | requires-python | win_amd64 | win_arm64 |
|---|---|---|---|---|
| numpy | 2.5.4 | >=3.12 | cp312, cp313, cp314, cp314t | same |
| scipy | 1.18.1 | >=3.12 | cp312, cp313, cp314, cp314t | same |
| psutil | 7.2.2 | >=3.6 | `cp37-abi3` (plus cp313t/cp314t) | `cp37-abi3` |
| sounddevice | 0.5.6 | >=3.7 | `py3-none-win_amd64` | `py3-none-win_arm64` |
| rpi-ws281x-mock | 0.2.2 | >=3.6 | pure `py2.py3-none-any` wheel | same |

Sources: `https://pypi.org/pypi/<name>/<version>/json` for each row.

Findings:
- All five have installable wheels for win_amd64 and win_arm64 on CPython 3.12-3.14. No compiler is needed.
- **numpy 2.5.4 and scipy 1.18.1 require Python >=3.12.** MLSC declares `numpy>=2.0,<3`, `scipy>=1.14,<2` and Python >=3.11; on 3.11 the resolver picks older numpy/scipy. Whether those older releases ship win_arm64 cp311 wheels was **not checked** (only latest releases were listed). Installing with `--python 3.12` (or later) avoids the question.
- sounddevice: pip installs on Windows bundle PortAudio, with two DLLs (with and without ASIO); the non-ASIO one loads by default. [sounddevice install docs](https://python-sounddevice.readthedocs.io/en/latest/installation.html)
- `music-led-strip-control` is not on PyPI yet: `https://pypi.org/pypi/music-led-strip-control/json` returned 404 on 2026-11-09. The one-liner cannot work until a release is published (or a `--from git+https://...` source is used).

## 2. Autostart options

Common constraint: audio capture needs audio endpoints reachable from the process.

### Session 0 and audio
- Services run in session 0 and "cannot directly interact with a user as of Windows Vista"; interactive services are deprecated, and `NoInteractiveServices` defaults to 1. [Interactive Services](https://learn.microsoft.com/en-us/windows/win32/services/interactive-services)
- WASAPI loopback (capture of a render endpoint, shared mode only, `AUDCLNT_STREAMFLAGS_LOOPBACK`): Microsoft states it "by default contains the mix of all audio being played, regardless of the Terminal Services session", and that "you can run a loopback client in a service running in session 0 and capture audio from all user sessions". [Loopback Recording](https://learn.microsoft.com/en-us/windows/win32/coreaudio/loopback-recording) So loopback from a service is documented as supported at the WASAPI level.
- Microphone capture from a session-0 service, and whether the Windows microphone privacy toggles apply to services: no primary source found (the Microsoft privacy page tried returned 404). **UNVERIFIED.**
- Whether PortAudio as bundled with sounddevice exposes WASAPI loopback: the sounddevice misc API page does not mention it; the platform-specific settings page was not read. **UNVERIFIED**; needs a check of `sd.WasapiSettings` and a test.
- A service runs as a separate account: "Each service executes in the security context of a user account"; options are LocalService, NetworkService, LocalSystem or a named user with password. [Service User Accounts](https://learn.microsoft.com/en-us/windows/win32/services/service-user-accounts) A service under another account would not see the user's `uv tool` install (`%USERPROFILE%`, `%APPDATA%`) or MLSC config.

### Options
| Option | Elevation | Runs | Notes (from the cited docs) |
|---|---|---|---|
| Startup folder shortcut (CSIDL_STARTUP) | none | at user logon | "The system starts these programs whenever the associated user logs on." Per-user folder. A shortcut stores target, arguments, working dir, show command and icon. [CSIDL](https://learn.microsoft.com/en-us/windows/win32/shell/csidl), [Shell Links](https://learn.microsoft.com/en-us/windows/win32/shell/links) |
| `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` value | none | at user logon | Command line max 260 chars; order indeterminate; ignored in Safe Mode; "the system may choose to delay" Run/Startup programs. [Run keys](https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys) |
| Task Scheduler, trigger "when a user logs on" | not stated; **UNVERIFIED** that a standard user can register a task for self | at logon, or boot | Triggers include "When a user logs on" and "When the system is booted". `Register-ScheduledTask` accepts `-Action`, `-Trigger`, `-Settings`, `-RunLevel Limited/Highest`, `-User`. [Task Scheduler](https://learn.microsoft.com/en-us/windows/win32/taskschd/task-scheduler-start-page), [Register-ScheduledTask](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/register-scheduledtask) Restart-on-failure settings not covered in the pages read (**UNVERIFIED**). |
| Real service via WinSW/NSSM | admin to install | at boot, before logon | WinSW `<serviceaccount>` supports `DomainName\UserName` plus `<password>`, and `<allowservicelogon>`. Its `<interactive>` option only lets the user switch to another window station on Vista+. [WinSW xml-config-file](https://github.com/winsw/winsw/blob/v3/docs/xml-config-file.md) NSSM docs (`nssm.cc/usage`) returned 503; NSSM facts **UNVERIFIED**. |

Trade-off summary: Startup folder and Run key are simplest, need no admin, and run in the user's own session (their audio endpoints and `%USERPROFILE%` tools available). Task Scheduler adds logon/boot choice and settings but is more code. A real service starts at boot but runs in session 0, needs admin plus a stored password to run as the user, and microphone behaviour there is unverified; loopback is documented as workable.

## 3. Windows Defender Firewall for 0.0.0.0:8080 plus UDP

- Default is block for inbound; "Explicitly defined allow rules take precedence over the default block setting" and "Explicit block rules take precedence over any conflicting allow rules". [Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)
- With no allow rule, the first listen/communication triggers a prompt. If the user is a local admin and clicks No or cancels, block rules are created (typically one for TCP, one for UDP). **If the user is not a local admin, block rules are created no matter what is selected.** Once block rules exist the prompt does not reappear; they must be deleted first. [Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)
- Microsoft states automatic rule creation "require[s] user interaction and administrative privilege", and recommends staging allow rules before first launch. Same page.
- Outbound is allowed by default, so MLSC's outbound UDP needs no rule; only the inbound TCP 8080 listener does. [Configure rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure)
- Creating rules: "If you are configuring a single device, you must have administrative rights on the device." [Configure rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure) No way to pre-create an inbound allow rule without admin is documented; the realistic design is **one elevation** running `New-NetFirewallRule` (NetSecurity module) with a program path and/or port. A program-plus-port rule limits traffic to that port and that program. Rules use the full executable path; wildcards are unsupported. [Configure rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure), [Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)
- Which exe is the "program": with `uv tool install`, `mlsc.exe` is a launcher copy and the listening image may be the venv's `python.exe`. This was **not verified**; a port-only rule (TCP 8080) avoids the ambiguity. The `New-NetFirewallRule` parameter details (`-Program`, `-LocalPort`, `-Profile`, `-Direction`) were not extracted from the reference page (output too large); check them before coding. [New-NetFirewallRule](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule)
- If local policy merge is disabled by Group Policy, locally created rules are not applied. [Firewall rules](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)
- Microsoft recommends scoping to the profiles that fit and, for home/small-network apps, restricting remote addresses to Local Subnet. Same page.

## 4. Start-menu shortcut that opens http://localhost:8080

- Per-user Start menu programs folder: CSIDL_PROGRAMS / FOLDERID_Programs ("...\Start Menu\Programs"). No admin needed. The all-users folder (CSIDL_COMMON_PROGRAMS) is the admin alternative. The modern literal path is not printed on the page; resolve it via the folder id or `[Environment]::GetFolderPath('Programs')` (the latter not verified against a primary source). [CSIDL](https://learn.microsoft.com/en-us/windows/win32/shell/csidl)
- `IShellLink` **cannot** create a link to a URL ("You cannot use IShellLink to create a link to a URL"). [Shell Links](https://learn.microsoft.com/en-us/windows/win32/shell/links)
- URL shortcuts are a different type: `WshShell.CreateShortcut("...\name.url")` returns a `WshURLShortcut`; set `TargetPath = "https://..."` and call `Save`. [CreateShortcut](https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/windows-scripting/xsy6k3ys(v=vs.84)) (archived page, still the primary reference for the object).
- Alternative `.lnk`: target a browser with the URL in **Arguments**, never in TargetPath ("A common problem is putting arguments in the TargetPath"). Same page. Icon via `IconLocation`.
- A `.url` file in the Programs folder is the simplest way for PowerShell (`New-Object -ComObject WScript.Shell`) to add "MLSC" to the Start menu. Whether Start search lists `.url` files like `.lnk` files is **UNVERIFIED**.

## Open items for a clean-VM test (not answerable from docs)
1. `uv tool install` on a machine with no Python: does it fetch Python, and which version?
2. sounddevice WASAPI loopback availability (`sd.WasapiSettings`) and microphone access under each autostart method.
3. Which process image the firewall prompt names; whether a port-only rule suffices.
4. Older numpy/scipy wheels on Python 3.11 for win_arm64.
5. `music-led-strip-control` release on PyPI.
