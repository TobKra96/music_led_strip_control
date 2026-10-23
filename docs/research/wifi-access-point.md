# Wi-Fi access point control from Python and the web UI (research #224)

Planning note for MLSC 3.0. Research only; no project code changed. Date: 2026-10-23.
Sources are primary only (NetworkManager docs and source, polkit docs, RFCs, this repo). Claims marked **[unverified]** could not be confirmed from a primary source.

## Short answer

- On Raspberry Pi OS with NetworkManager (NM), the supported way to run an AP is a NM connection profile with `802-11-wireless.mode=ap` and `ipv4.method=shared`. NM then provides DHCP, DNS forwarding and NAT itself, so hostapd and dnsmasq services are not needed.
- MLSC already requires root (`server/main.py` exits with "Run MLSC as root (sudo)" if it cannot open its lock file in a root-only path). Root requests are always granted by NM's polkit check, so no polkit rule or sudoers entry is needed for the default deployment.
- Recommended integration: a small backend module that shells out to `nmcli` (terse mode) for the first version, with `sdbus-networkmanager` as the later, typed option. Keep a mock backend for Windows/WSL development.
- Lock-out safety is the hardest part and is mostly design, not API: never tear down the client connection without a rollback timer, and never replace the only working uplink with an AP unless the user is already connected through another path.

## 1. NetworkManager AP mechanics

| Fact | Source |
|---|---|
| `nmcli device wifi hotspot [ifname IFNAME] [con-name NAME] [ssid SSID] [band {a\|bg\|6GHz}] [channel CHANNEL] [password PASSWORD]` creates a hotspot profile matching the device capabilities and activates it. Stop with `connection down` or `device down`. Without `password`, nmcli generates one; global `-s` prints it. | [nmcli manual](https://networkmanager.dev/docs/api/latest/nmcli.html) |
| Profile settings: `802-11-wireless.mode` is one of infrastructure, mesh, adhoc, ap; `band` is `a` (5 GHz), `bg` (2.4 GHz) or `6GHz`; `channel` requires `band`; `ssid` is required; `hidden` is available. | [nm-settings-nmcli](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html) |
| `802-11-wireless-security.key-mgmt`: `wpa-psk` (WPA2 and WPA3 personal), `sae` (WPA3 only), `owe`. WPA-PSK passphrase is 8 to 63 ASCII characters or 64 hex. `pmf` default uses the global default (optional if none). | [nm-settings-nmcli](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html) |
| `ipv4.method=shared`: with no manual address NM chooses a 10.42.x.0/24 subnet, forwarding is always enabled, DHCP range is derived from the interface address, default lease is one hour. Must be set on the interface that serves clients, not on the uplink. | [settings-ipv4](https://networkmanager.dev/docs/api/latest/settings-ipv4.html), [nm-settings-nmcli](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html) |
| NAT/masquerading for shared mode is done via the `firewall-backend` setting (`iptables`, `nftables` or `none`). | [NetworkManager.conf](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html) |
| Shared mode launches its own dnsmasq with `--conf-file=/dev/null`, `--bind-interfaces`, `--listen-address=<gateway>`, `--dhcp-range=...`, `--dhcp-option=option:router,...`, and `--conf-dir=<NMCONFDIR>/dnsmasq-shared.d` if that directory exists. | [nm-dnsmasq-manager.c](https://github.com/NetworkManager/NetworkManager/blob/main/src/core/dnsmasq/nm-dnsmasq-manager.c) |
| The device reports AP support as capability flag `NM_WIFI_DEVICE_CAP_AP = 0x40` in `Device.Wireless.WirelessCapabilities`; 5 GHz is `0x400`, 6 GHz `0x800`. | [nm-dbus-types](https://networkmanager.dev/docs/api/latest/nm-dbus-types.html), [Device.Wireless](https://networkmanager.dev/docs/api/latest/gdbus-org.freedesktop.NetworkManager.Device.Wireless.html) |
| Autoconnect: `connection.autoconnect`, `autoconnect-priority` (-999..999, higher preferred), `autoconnect-retries` (-1 default 4, 0 forever). Autoconnect never competes with an already active profile. | [nm-settings-nmcli](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html) |
| `connection down` leaves the device free to auto-activate another profile and blocks the downed profile from autoconnect until modified or explicitly activated. Docs say `device down` is usually preferable. Default timeouts: `up` 90 s, `down` 10 s. | [nmcli manual](https://networkmanager.dev/docs/api/latest/nmcli.html) |
| Keyfile profiles live in `/etc/NetworkManager/system-connections/`; files readable or writable by anyone but root are ignored (they hold plaintext secrets). Run `nmcli con reload` after manual edits. | [nm-settings-keyfile](https://networkmanager.dev/docs/api/latest/nm-settings-keyfile.html) |
| Wi-Fi backend defaults to wpa_supplicant; iwd is marked experimental. | [NetworkManager.conf](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html) |

A suggested persistent profile (create once, then toggle):

```
nmcli connection add type wifi ifname wlan0 con-name mlsc-ap ssid MLSC-Setup \
  802-11-wireless.mode ap 802-11-wireless.band bg 802-11-wireless.channel 6 \
  wifi-sec.key-mgmt wpa-psk wifi-sec.psk "<8-63 chars>" \
  ipv4.method shared ipv6.method disabled \
  connection.autoconnect no
```

Values are taken from the settings reference above; the exact command has not been run on a Pi. **[unverified on hardware]**

## 2. Control interfaces from Python

1. **nmcli via subprocess (recommended first step).** Documented script-friendly output: `-t/--terse`, `-f/--fields`, `-g/--get-values`. Matches the repo's existing style (it already shells out for `amixer`, `systemctl`, `vcgencmd`). Always pass argument lists (no `shell=True`) and never put the passphrase on a logged command line.
2. **`sdbus-networkmanager`.** Python bindings for the NM D-Bus API, async (`sdbus_async.networkmanager`) and blocking (`sdbus_block.networkmanager`) variants, installed with `pip install --only-binary ':all:' sdbus-networkmanager`, licensed LGPL-2.1 / GPL-2.0 ([repo](https://github.com/python-sdbus/python-sdbus-networkmanager)). Benefits: typed errors, signals (watch `LastScan`, state changes) instead of polling. Cost: new dependency and a native-wheel requirement on 32-bit Pi OS **[unverified]**; the repo page did not state a Python version, a release number, or show an AP example.
3. **Raw D-Bus.** `AddAndActivateConnection` with a settings dict is the underlying call for either option; not worth using directly.
4. **PyGObject / libnm.** Not researched in depth; heavier system dependency than the above.

Recommendation: define a `WifiManager` interface (status, scan, start_ap, stop_ap, connect_client) in the backend, implement `NmcliWifiManager` first, keep D-Bus as a drop-in later.

## 3. Privileges

- NM authorizes non-root callers through polkit unless `[main] auth-polkit` is changed. Root is always granted; `false` allows everything; `root-only` denies non-root ([NetworkManager.conf](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html)).
- Default polkit policy, from NM's [`data/org.freedesktop.NetworkManager.policy.in`](https://github.com/NetworkManager/NetworkManager/blob/main/data/org.freedesktop.NetworkManager.policy.in):
  - `settings.modify.system` (add or edit system profiles): `auth_admin_keep` for any/inactive/active.
  - `network-control`: any = `auth_admin`, inactive/active = `yes`.
  - `wifi.share.protected` and `wifi.share.open`: inactive `no`, active `yes` (any not set in the file, so the polkit default applies).
  - `enable-disable-wifi`: inactive `no`, active `yes`.
- A systemd service has no active local session, so for a non-root service the defaults would require auth. Options if MLSC ever drops root: a polkit rule in `/etc/polkit-1/rules.d/` granting `polkit.Result.YES` to the service user for the specific `org.freedesktop.NetworkManager.*` action ids, using `subject.user`. The polkit manual says rules files are meant for administrators and special-purpose systems ([polkit(8)](https://www.freedesktop.org/software/polkit/docs/latest/polkit.8.html)), which fits an appliance image.
- sudoers entries for `nmcli` are possible but give broad control (nmcli can edit any profile); a polkit rule scoped to action ids is narrower. Capabilities (`CAP_NET_ADMIN`) do not replace NM authorization, since NM does the work. Not verified in a primary source beyond the above.
- Today: root-only, so nothing to configure. The web UI must therefore treat the Wi-Fi endpoints as high-risk (they are effectively root-equivalent network control) and be behind the existing login (`flask_login` is used in `server/libs/app`).

## 4. hostapd + dnsmasq alternative

- Possible but not recommended on NM systems: NM and hostapd would both want the interface, so the interface must be marked unmanaged, and DHCP/DNS/NAT/firewall must be configured by hand. hostapd's own config is documented in its example [`hostapd.conf`](https://git.w1.fi/cgit/hostap/plain/hostapd/hostapd.conf); that page was blocked by bot protection during this research, so no settings were verified. **[unverified]**
- Note the repo's System Info page lists `hostapd`, `NetworkManager` and `dnsmasq` as services to check (`server/libs/webserver/blueprints/system_info_executer.py`). That listing should be reduced to `NetworkManager` if the NM route is adopted.

## 5. Captive portal and first-boot onboarding

- NM's shared dnsmasq reads extra config from `<NMCONFDIR>/dnsmasq-shared.d` (source above), so a DNS catch-all for the AP (a dnsmasq `address=/#/<gateway>` line) can be dropped in there. The dnsmasq directive itself was not checked in dnsmasq's manual during this research. **[unverified]** The `NetworkManager.conf` docs do not mention `dnsmasq-shared.d`; it is visible only in source, so treat it as an implementation detail that could change.
- RFC 8910 defines DHCPv4 option 114 and an IPv6 RA option (type 37) to advertise a captive-portal API URI; it does not require HTTPS but notes TLS helps trust ([RFC 8910](https://www.rfc-editor.org/rfc/rfc8910.html)). Whether NM's shared dnsmasq can emit option 114 via `dnsmasq-shared.d` (`dhcp-option=114,...`) is plausible but **[unverified]**.
- Simplest robust onboarding: AP up on first boot when no client profile is connected; any HTTP request to the Pi (DNS catch-all) lands on a Wi-Fi setup page in the MLSC web UI; user picks SSID and enters a password; the app saves the client profile, drops the AP, joins. Phones' own captive-portal detection behavior was not researched from vendor docs. **[unverified]**
- Current docs say Pi OS disables networking on dual-band devices until a Wi-Fi country is set ([Raspberry Pi configuration docs](https://www.raspberrypi.com/documentation/computers/configuration.html)), so the setup flow must ensure a regulatory country is configured before starting an AP (band and channel choices depend on it).

## 6. Lock-out safety

Design rules derived from the documented NM behavior:

1. A single Wi-Fi radio is usually either client or AP. Whether the Pi's chip supports concurrent AP + station is **[unverified]** here; check `iw list` "valid interface combinations" on target hardware before promising it.
2. Switching to AP drops the user's current Wi-Fi session, including the browser tab that issued the request. The UI must warn first and show the AP SSID/password and the address to browse (`10.42.0.1` is the default gateway only when NM picks the first subnet; set `ipv4.addresses` explicitly to make it deterministic).
3. Use a rollback timer: apply the change, wait for confirmation from a client on the new network, otherwise revert to the previous profile after N seconds. NM has a checkpoint/rollback D-Bus API (`checkpoint-rollback` appears in the polkit policy) which could back this; its semantics were not researched. **[unverified]**
4. Prefer an automatic AP fallback: a low `autoconnect-priority` AP profile that only comes up when no client profile can connect. Caveat from the docs: autoconnect never competes with an already active profile, and `autoconnect-retries` caps attempts, so a "client failed, now bring AP up" watchdog in the app is still needed.
5. Never use `connection down` alone on the client profile: it blocks that profile from autoconnect until modified, which can strand the device. Prefer `device down` or explicit `connection up` of the target.
6. Recovery path outside the web UI: document an `nmcli connection up <client>` fix over SSH/serial, and an Ethernet fallback. A physical trigger (long-press GPIO or file on `/boot`) is an optional extra.

## 7. Windows / WSL development

- NM does not run on native Windows. WSL2 has no real Wi-Fi radio for the Linux guest, so AP mode cannot be exercised there. Whether WSL2 can run NM at all was not researched. **[unverified]**
- Plan: the `WifiManager` interface plus a `MockWifiManager` (in-memory state, fake scan results, simulated delays and failures, including the "connection lost after apply" case) selected by platform or config flag. Test the `nmcli` backend by feeding recorded terse outputs to its parsers; run integration tests only on a real Pi.

## 8. Recommendation

1. Use NM profiles (`mode=ap`, `ipv4.method=shared`, WPA2/WPA3 PSK) rather than hostapd/dnsmasq.
2. Implement behind a `WifiManager` interface; start with `nmcli` subprocess (argument lists, terse mode), keep the door open for `sdbus-networkmanager`.
3. Stay with root (current model); no polkit or sudoers work needed. Document the polkit-rule route as the path if MLSC ever runs unprivileged.
4. Build onboarding as: AP on boot if no client connectivity, setup page, then join with rollback timer.
5. Ship a mock backend for Windows/WSL; verify on real Pi hardware before release.

## Open uncertainties

- Concurrent AP + client on the Pi's Wi-Fi chips (needs `iw list` on target models).
- Exact `nmcli connection add` option names for AP on the NM version shipped in the latest Pi OS (check `nmcli --version`; the docs here are "latest").
- dnsmasq catch-all and option 114 inside `dnsmasq-shared.d`; phone captive-portal detection behavior.
- NM checkpoint/rollback semantics for the safety timer.
- hostapd settings (source page blocked).
- Security of the setup AP: password handling, whether to leave the AP open for onboarding (`owe` or open `wifi.share.open` path) versus a printed per-device PSK.
