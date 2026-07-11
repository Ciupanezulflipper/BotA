# Targeted Clock and Heartbeat Diagnostic

- [proven] Valid HTTP date sources: `3`.
- [proven] Local-minus-server drift seconds: `-7267`.
- [inferred] Clock root cause: `DEVICE_CLOCK_UNSAFE`.
- [proven] Android automatic time: `cmd: Failure calling service settings: Failed transaction (2147483646)`.
- [proven] Android automatic time zone: `cmd: Failure calling service settings: Failed transaction (2147483646)`.
- [proven] Expected heartbeat environment exists: `False`.
- [proven] Expected environment has Telegram token variable: `False`.
- [proven] Expected environment has Telegram chat-ID variable: `False`.
- [proven] Runtime environment has Telegram token variable: `True`.
- [proven] Runtime environment has Telegram chat-ID variable: `True`.
- [inferred] Heartbeat root cause: `HEARTBEAT_USES_OBSOLETE_ENV_PATH`.
- [proven] Runtime-health push age seconds: `235`.
- [proven] Runtime-health recent pass: `True`.
- [proven] Runtime-health delivery repair is not required.
- [proven] Strategy changes remain unauthorized.
