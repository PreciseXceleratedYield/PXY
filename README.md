# PXY — PreciseXceleratedYield

PXY is an automated NIFTY options-trading platform. It combines market-data
ingestion, independently configured entry and exit signal channels, broker
order execution, position/exit management, averaging, portfolio-risk controls,
and a Node.js web dashboard.

The production runtime is configured in one place:
`pxy/sys/syscnfgpxy.py`. The documentation describes the current code; when
there is a discrepancy, the implementation is authoritative.

## Repository guide

- [INFO.md](INFO.md) — system architecture, signal definitions, execution flow,
  and operator-oriented overview.
- [READ.md](READ.md) — concise operational notes and safe navigation.
- [Runtime configuration](pxy/sys/CONFIGURATION.md) — configuration ownership,
  current strategy rules, timing, and conditional settings.
- [CHANGELOG.md](CHANGELOG.md) — notable repository changes.

## Production layout

```text
pxy/
├── pxy                 # Interactive management menu; starts web and engine
├── pxy.js              # Node.js web application
├── sys/
│   ├── sysexepxy.py    # Engine supervisor
│   ├── syscnfgpxy.py   # Single runtime configuration source
│   ├── sysdtafpxy.py   # Market-data ingestion
│   ├── sysdthapxy.py   # Candle transformations and depth analysis
│   ├── sysinpxy.py     # Entry signal channel
│   ├── sysoutpxy.py    # Exit signal channel
│   ├── sysmktpxy.py    # IN/OUT signal router
│   ├── sysentrpxy.py   # Entry-window and cooldown router
│   └── exe/            # Execution pipelines and run-directory utilities
└── web/                # Dashboard pages and published UI data
```

The repository also contains retained material under `pxy/_/` and other
standalone utilities. Their presence does not make them part of the production
launch path.

## Production launch

On the configured host, the interactive `pxy/pxy` management script resolves
the application directory and Python environment. Its **Start** action launches
the Node.js dashboard in tmux session `pxy-web` and the Python supervisor in
`pxy-engine`. The supervisor runs the production execution loop.

Do not use a generic `pip install` recipe or copy credentials into a new local
configuration file. Follow the host's established environment and secret
provisioning. Starting the production engine can place live broker orders.

## Configuration and strategy

- Timezone: `Asia/Kolkata`.
- Production underlying ticker: `^NSEI`; `BTC-USD` is monitor-only.
- DTHA, IN, and OUT have independent candle-mode settings.
- Supported candle modes: `RAW`, `OC2`, `HA`, `OHLC4`, `HYPER`, `TSMA`.
- The TSMA candle transformation period is configured separately from the
  50-period chart moving average.
- Entry/exit signals are based on transformed-close direction, not a
  Supertrend/SMA confirmation stage.
- Broker execution, averaging, targets, and portfolio risk are governed by
  the active execution modules and central configuration.

See [INFO.md](INFO.md) and
[pxy/sys/CONFIGURATION.md](pxy/sys/CONFIGURATION.md) for the detailed current
behaviour. This README intentionally avoids duplicating every runtime default.
