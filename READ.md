# PXY — Operator Read-Me

This file is a short navigation and operating note for the current repository.
It replaces obsolete personal text and retired installation instructions.

## Before operating

1. Confirm you are on the intended repository and branch.
2. Review `pxy/sys/syscnfgpxy.py` and
   `pxy/sys/CONFIGURATION.md` for the active runtime settings.
3. Confirm the host's configured Python environment and broker session.
4. Remember that starting the production engine can submit live orders.

## Management entry point

The production host uses the interactive `pxy/pxy` management script.

- **Start** launches the Node.js dashboard (`pxy-web`) and Python engine
  supervisor (`pxy-engine`) in tmux.
- **View** displays the engine tmux output.
- **Enter** opens the manual trading operations menu.
- **Test** runs a selected Python script; do not select scripts without
  understanding whether they access the broker.
- **Update** runs the repository's update workflow.
- **Stop** terminates the managed engine and web sessions.

Use the menu deliberately. Do not start a second engine process alongside the
managed `pxy-engine` session.

## Production execution path

```text
pxy/pxy
  ├── pxy.js                         (web dashboard)
  └── sys/sysexepxy.py               (supervisor)
        └── sys/exe/exepxy.py         (production execution loop)
              ├── run/runnfutpxy.py
              ├── exeexitpxy.py
              ├── exeentrpxy.py
              └── exeavgpxy.py
```

The execution loop prioritizes exits around entry and averaging passes. Each
child script is launched with the configured pipe timeout. A failed component
is recorded and retried on later iterations; persistent component failures
are periodically reported through Telegram.

## Where to look

- Runtime settings: `pxy/sys/syscnfgpxy.py`
- Configuration rules: `pxy/sys/CONFIGURATION.md`
- Architecture and signal definitions: `INFO.md`
- Change history: `CHANGELOG.md`

Do not use old setup snippets that delete repository contents, download
unverified scripts, or create parallel runtime configuration files.
