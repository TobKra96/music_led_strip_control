# Web stack options for MLSC 3.0 (ticket #222)

Research date: 2026-10-23. Planning only; no project code changed.
Sources are primary only: PyPI JSON API, GitHub repository metadata/releases (via `gh api`), and official project documentation. Each claim names its source in brackets.

## Question

Is Flask (waitress, Flask-Login, Flask-OpenAPI3-UI) still current? What are better or more comfortable options for a Pi-hosted control UI (FastAPI, Litestar, Quart, NiceGUI, others): live updates, OpenAPI, auth, Pi 4 / Zero 2 footprint, pip-install friendliness, and rewrite cost?

## Short answer

- **Flask itself is current and maintained.** Latest 3.1.3 (2026-02-18); repo pushed 2026-10-07 [PyPI, GitHub pallets/flask]. The repo pins 3.1.2; 3.1.3 is a security fix (session `Vary: Cookie` handling, GHSA-68rp-wp8r-4726) and should be taken now [Flask changelog].
- **The weak links are the extensions, not Flask.**
  - **Flask-OpenAPI3-UI 2.3.0**: last release 2023-11-24; its repository (overflowdigital/Flask-OpenAPI) is **archived**, last push 2024-05-06 [PyPI, GitHub]. It is a Flasgger-derived package.
  - **Flask-Login 0.6.3**: last release 2023-10-30, but the repo is still active (pushed 2026-10-07). Its master already removed `LOGIN_DISABLED` (commit "Remove LOGIN_DISABLED config (#868)", 2024-09-15) [GitHub maxcountryman/flask-login]. MLSC uses `LOGIN_DISABLED` in `authentication_executer.py`, so the next Flask-Login release will break that code path. The code already carries a TODO about this.
  - **waitress 3.0.2**: last release 2024-11-16, repo pushed 2026-09-27, not archived [PyPI, GitHub]. Fine, but WSGI-only, with no WebSocket support documented [waitress docs].
- **Flask can do live updates without a rewrite**, with caveats: SSE through streaming generators works on a threaded WSGI server [Flask streaming docs]; Flask-Sock WebSockets document support for Werkzeug, Gunicorn, eventlet and gevent but **do not mention waitress** [Flask-Sock docs]. WebSockets would therefore mean replacing waitress (Gunicorn is Unix-only, so Windows dev would use Werkzeug).
- **Recommendation:** staying on Flask is defensible and the lowest cost. The improvement worth making regardless of framework is to **replace Flask-OpenAPI3-UI** (archived) with a maintained spec source. If 3.0 wants real-time push and typed OpenAPI as first-class features, **FastAPI** is the most comfortable move. The executer layer is almost framework-agnostic, so the rewrite cost is moderate rather than total. See "Recommendation" for the decision the user needs to make.

## Current stack and rewrite sizing

Measured in this repo (server/libs):

| Part | Size | Framework coupling |
| --- | --- | --- |
| `webserver/blueprints/*_executer.py` (business logic) | 954 lines | Almost none. Only `authentication_executer.py` imports Flask / Flask-Login; `messages.py` imports `Response, jsonify` |
| `webserver/blueprints/*_api.py` (46 route handlers, 9 blueprints) | 699 lines | Full: `Blueprint`, `request`, `jsonify`, `@login_required`, `@swag_from` |
| `webserver/blueprints/docs/**/*.yml` (Flasgger-style per-route OpenAPI YAML) | 2,430 lines | Tied to `swag_from`; reusable as source material, not directly |
| `webserver/schemas/*` (jsonschema validators, config validator) | about 2,300 lines | None (plain `jsonschema`) |
| Jinja templates (`app/templates`, 44 files; 28 are per-effect pages) | 4,323 lines, 492 Jinja tags | Jinja2 is framework-neutral; `url_for` / `render_template` / `segment` context would need equivalents |
| Own JS (`dashboard`, `system`, `settings.*`, classes) | about 1,700 lines, jQuery `$.ajax` against `/api/*` | None. Talks to REST only |
| Live updates today | `setTimeout` polling every 10 to 20 s in `system.js`; no WebSocket / SSE | Nothing to port |
| Server | `waitress.serve(..., threads=8)`; Flask `secret_key` regenerated per start | |

Consequences:

1. The front end is a REST client of `/api/*`. Any option that keeps the REST contract keeps all JS unchanged.
2. A framework swap rewrites roughly 700 lines of route glue plus auth wiring and OpenAPI metadata. It does not touch the executers (apart from one auth file and `messages.py`) or the validators.
3. The Jinja templates move with minimal edits to Jinja-capable frameworks (Flask, Quart, FastAPI, Litestar via Jinja2 template engine). NiceGUI would replace them entirely.
4. The webserver runs inside the MLSC process and talks to the LED/audio side through queues, via `Executer`. Async frameworks can call these synchronous executers through a thread pool; behavior to verify in a spike, not documented anywhere as a given.

## Options

Versions below are PyPI latest as of 2026-10-23 [PyPI JSON API]. "Pure" means the latest release ships only pure-Python (`py3-none-any`) wheels / sdist.

| Option | Latest (date) | Python | Maintenance | Live updates | OpenAPI | Auth | Install | Rewrite cost for MLSC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **A. Stay on Flask 3.1.3 + waitress** | Flask 3.1.3 (2026-02-18), waitress 3.0.2 (2024-11-16) | >=3.9 | Flask active; waitress active-ish, not archived | SSE via generators [Flask docs]; WebSocket not on waitress | via extension (see B) | Flask-Login 0.6.3 (stale release, active repo, breaking change pending) | Pure, no native deps | None (bump pin) |
| **B. Flask + replace OpenAPI extension** (flask-openapi3 4.3.2, 2026-05-09, pydantic based; or flask-smorest 0.47.0, 2026-03-22, marshmallow based) | see left | >=3.10 | flask-openapi3 repo pushed 2026-10-10, latest tag v5.0.0 on GitHub (2026-10-10; PyPI latest still reads 4.3.2 at query time) | same as A | generated from typed models; replaces 2,430 lines of YAML over time | same as A | Pure; adds pydantic (has native wheels) or marshmallow | Low to moderate: re-annotate 46 handlers |
| **C. Flask + Flask-Sock (WebSocket)** | Flask-Sock 0.7.0 (2023-10-02), repo pushed 2026-08-29 | >=3.6 | Active repo, rare releases | WebSocket; documented servers Werkzeug, Gunicorn, eventlet, gevent [Flask-Sock docs] | n/a | same as A | Pure | Low for code, but waitress would be dropped; Gunicorn threads: each WebSocket client occupies a worker or thread [Flask-Sock docs] |
| **D. FastAPI 0.161.1 + uvicorn 0.54.0** | 2026-10-22 / 2026-09-25 | >=3.10 | Very active (pushed 2026-10-22) | WebSocket native; **SSE native** (`EventSourceResponse`, added in FastAPI 0.135.0, auto keep-alive ping every 15 s) [FastAPI docs] | Built in; generated from Pydantic types | Roll your own or add dependencies (`Depends`, `Security` supported, also on WebSocket) [FastAPI docs]; no session/login manager shipped | Pure Python itself; pydantic-core is a native wheel (wheel availability on 32-bit Pi OS is unverified) | Moderate: rewrite 46 handlers, auth, template wiring; JS and executers unchanged |
| **E. Litestar 2.25.0** | 2026-10-18 | >=3.8, <4 | Active (pushed 2026-10-20; 359 open issues) | WebSocket listeners / streams; `ServerSentEvent` response [Litestar docs] | Automatic OpenAPI 3.1 [Litestar docs] | Built-in JWT and session auth backends, guards [Litestar docs] | Pure for litestar; pulls msgspec and multidict etc. (native wheels, availability on 32-bit unverified) | Moderate, similar to D, but more built in (auth, sessions) |
| **F. Quart 0.23.1** | 2026-08-29 | **>=3.13** | Pallets project, active | WebSocket and SSE documented [Quart docs] | via extensions (e.g. quart-schema; not checked) | Flask-style extensions; some Flask extensions work | Pure; needs hypercorn | Lowest rewrite of the async options (Flask-like API), but Python >=3.13 excludes Debian Bookworm's Python and any older Pi OS |
| **G. NiceGUI 3.18.0** | 2026-10-07 | >=3.10 | Very active (pushed 2026-10-23) | Built in: UI state pushed over socket.io (python-socketio dependency) | Optional (`fastapi_docs`), built on FastAPI [NiceGUI docs] | Not covered by deployment docs; session storage with `storage_secret` | Pure python; many dependencies (aiohttp, fastapi, uvicorn[standard], orjson, pydantic-core, ...) | **Highest**: replaces templates and JS (about 6,000 lines) by Python UI code; REST stays possible through FastAPI. Runtime cost is higher: `binding_refresh_interval` default 0.1 s timer [NiceGUI docs] |

Not considered further: Sanic 25.12.1 (needs uvloop/httptools native extensions), aiohttp, Granian (native Rust wheels). No advantage for this project was found in their docs relative to D and E; this was a judgement call, not exhaustive research.

### Notes per concern

**Live updates.** The UI has no push today; it polls every 10 to 20 s. Sub-second feedback (VU meters, strip preview, device status) would benefit from SSE or WebSocket. SSE is the smaller requirement for a mostly server-to-client dashboard, and works on all options (A via generators, D and E natively). Browser `EventSource` is GET-only [FastAPI docs note], which is fine here because control actions stay as REST POSTs.

**OpenAPI.** Today it is hand-written Flasgger-style YAML (2,430 lines) wired by `@swag_from` and a vendored Swagger UI. Typed frameworks (D, E, flask-openapi3) derive the spec from models, which would let the existing jsonschema validators be replaced or generated. That is a separate, optional consolidation.

**Auth.** Current auth is a PIN with Flask-Login, `LOGIN_DISABLED` when PIN is off, session secret regenerated at start. FastAPI has no login manager; Litestar ships session and JWT backends; Flask options stay as-is until Flask-Login's next release removes `LOGIN_DISABLED` (needs replacing with a simple `before_request` check or a custom decorator).

**Pi 4 / Zero 2 footprint.** No primary benchmark exists for this workload. The only first-party numbers found are configuration defaults (for example NiceGUI's 0.1 s binding loop) and dependency lists (waitress has no dependencies; Flask has 7; FastAPI about 6 plus Starlette, anyio, pydantic and uvicorn; NiceGUI about 25). Whether the extra RAM matters on a Zero 2 (512 MB) beside the audio/LED process is unmeasured here. A 1-hour spike measuring RSS idle and under SSE load on the actual hardware is the only trustworthy answer.

**pip-install friendliness.** Flask/waitress/Flask-Login are pure Python today. Options D, E, G add pydantic-core or msgspec, which ship as compiled wheels; their availability on the user's Pi platforms (armv7l 32-bit vs aarch64) was not verified from primary sources in this pass. The Raspberry Pi docs state Raspberry Pi OS is based on Debian Trixie, and that 32-bit images target older models such as Pi Zero, with 64-bit for Pi 3, 4, 5 [Raspberry Pi docs]; they do not say which to use on the Zero 2 or give a Python version. The repo README claims Python 3.9+.

## Recommendation

1. **Now, independent of the choice:** bump `Flask` to 3.1.3 (security fix).
2. **Default pick: stay on Flask for 3.0** and plan two surgical replacements:
   - Replace archived Flask-OpenAPI3-UI with flask-openapi3 (or accept the YAML approach with plain Swagger UI file served statically), and
   - Replace the `LOGIN_DISABLED` usage so Flask-Login upgrades do not break.
   Add SSE (generator based) for live status if push is wanted; this works with waitress without new dependencies. Cost: low; JS, templates, executers untouched.
3. **If 3.0 should have first-class WebSocket/SSE and typed API:** FastAPI (D) is the most comfortable option: the largest ecosystem, native SSE and WebSocket, built-in OpenAPI. Litestar (E) is the alternative if built-in session auth matters. Both keep the REST contract so the JS front end is untouched. Cost: moderate (about 700 lines of routes plus auth plus templates wiring).
4. **Avoid** Quart unless the minimum supported Python becomes 3.13, and NiceGUI unless the UI is to be rewritten in Python.

User choice needed: A/B (stay on Flask, low cost) versus D or E (async framework, moderate cost, better live updates).

## Open uncertainties

- Pi RAM/CPU for each option: unmeasured; needs an on-device spike (Pi 4 and Zero 2).
- Wheel availability of pydantic-core / msgspec / orjson for armv7l (32-bit Pi OS): not verified.
- Minimum Python on target Pi OS images (Bookworm vs Trixie) for MLSC users: not stated in the Raspberry Pi docs consulted.
- flask-openapi3 version: PyPI showed 4.3.2 while the GitHub latest release is v5.0.0 (2026-10-10); check which is installable and its breaking changes before adopting.
- Whether async frameworks interact cleanly with the existing queue-based `Executer` singleton: untested; expected to work through a thread pool.
- Quart OpenAPI story (quart-schema) not researched.
- Flask-Sock behavior under waitress: undocumented; not tested.

## Sources

- PyPI JSON API (`https://pypi.org/pypi/<package>/json`) for flask, waitress, flask-login, flask-openapi3-ui, flask-openapi3, flask-smorest, flask-sock, fastapi, starlette, uvicorn, litestar, quart, nicegui, sanic, granian (queried 2026-10-23).
- GitHub repository metadata and releases via `gh api`: pallets/flask, maxcountryman/flask-login, overflowdigital/Flask-OpenAPI (archived), Pylons/waitress, fastapi/fastapi, litestar-org/litestar, pallets/quart, zauberzeug/nicegui, luolingchun/flask-openapi, miguelgrinberg/flask-sock.
- Flask changelog: https://flask.palletsprojects.com/en/stable/changes/ ; streaming: https://flask.palletsprojects.com/en/stable/patterns/streaming/
- Waitress docs: https://docs.pylonsproject.org/projects/waitress/en/stable/
- Flask-Sock docs: https://flask-sock.readthedocs.io/en/latest/ and /web_servers.html
- FastAPI: https://fastapi.tiangolo.com/advanced/websockets/ and /tutorial/server-sent-events/
- Litestar: https://docs.litestar.dev/latest/usage/websockets.html, /usage/responses.html, /usage/openapi/index.html, /usage/security/index.html
- Quart: https://quart.palletsprojects.com/en/latest/
- NiceGUI deployment/config: https://nicegui.io/documentation/section_configuration_deployment
- Raspberry Pi OS: https://www.raspberrypi.com/documentation/computers/os.html
- Repo measurements: `server/libs/webserver/**`, `server/libs/app/**`, `requirements.txt`, `README.md` at commit adcc5fd.
