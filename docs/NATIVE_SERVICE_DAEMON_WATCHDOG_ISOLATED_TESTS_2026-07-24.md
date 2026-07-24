# Isolated validation record

The native service-daemon watchdog was built and tested outside the phone runtime.

Validation completed before publishing the branch:

- `python3 -m py_compile` passed for implementation and tests.
- `bash -n` passed for the detached launcher.
- Nine focused unit tests passed.
- A regression scan found no direct `runsvdir -P`, `Popen(...runsvdir)`, or `launch_manager` path in the new implementation.
- Local Git blob hashes matched the files uploaded to GitHub exactly.

Covered cases:

1. Healthy native manager is a no-op.
2. Multiple managers fail closed.
3. Existing non-native manager without the native PID file fails closed.
4. Missing manager starts only the native Termux service daemon.
5. Proven-dead stale PID file is removed before native start.
6. Live non-manager PID referenced by the PID file blocks recovery.
7. Manager-owned down service receives bounded `sv up`.
8. PID 1 orphan is handed to the native manager one service at a time.
9. Delayed `runsv` supervisor appearance is bounded before failure.
10. PID-file/manager mismatch fails closed.

No phone, strategy, signal, Telegram, Supabase, provider, or Lifvio state was changed.
