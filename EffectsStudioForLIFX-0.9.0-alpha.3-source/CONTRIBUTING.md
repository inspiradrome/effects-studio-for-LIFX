# Contributing

Bug reports and focused pull requests are welcome. For effect or device-mapping
changes, please describe the LIFX model and firmware used for physical testing.

## Development

Effects Studio for LIFX currently uses Python 3.12 on Windows.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
node --check effects_studio\static\app.js
```

Please avoid committing real device serials, IP addresses, saved settings, or
build output. Keep hardware writes scoped to an explicitly selected device and
preserve the native-state restoration behaviour.
