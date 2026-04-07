# BOTA REMAINING FIXES MAP

Last updated: 2026-04-08

---

## 1) FIXED

### OPS-001 / OPS-002 — Cron Python execution mode
Status: FIXED

Proof:
- `restore_cron.txt` cleaned and reinstalled into active crontab
- active crontab now runs:
  - `python3 .../alerts_to_trades.py`
  - `python3 .../pause_guard.py`

Notes:
- Historical shell syntax errors may remain in old log lines
- active cron wiring is corrected

---

### OPS-003 / OPS-004 — Shadow manager env bootstrap and scheduling
Status: FIXED

Proof:
- `tools/run_shadow_manager.sh` created and verified
- manual wrapper smoke test passed
- shadow manager cron line added to active crontab
- log showed:
  - `Schema compatibility: PASS`
  - `OANDA_MODE=PRACTICE`
  - normal manager completion

Notes:
- startup/config blocker is resolved
- scheduling path now exists in active cron

---

## 2) IN_PROGRESS

### STRAT-002 — Duplicate shadow rows / storage-boundary uniqueness
Status: IN_PROGRESS

Proof:
- Codex audit identified weakest boundary at shadow manager storage layer
- `tools/be_shadow_manager.py` updated with uniqueness-contract guard in `ensure_shadow_row()`
- markers present:
  - `UNIQ_CONFLICT_ERR`
  - `UNIQUE CONTRACT ERROR`
- `py_compile` passed
- wrapper smoke test passed after replacement

What is proven:
- future insert path now has fail-closed protection if `(signal_id, policy)` uniqueness is not enforced

What is NOT yet proven:
- guard has not been exercised by a live active-signal insert
- this does not yet prove duplicate elimination for different upstream `signal_id`s
- historical duplicate rows are not cleaned by this change

Next proof step:
- wait for scheduled run with active signals
- inspect:
  - `logs/cron.shadow.log`
  - `logs/shadow_manager.log`
  - `logs/shadow_manager_heartbeat.txt`
  - real `ensure_shadow_row()` path execution

---

### STRAT-001 / STRAT-006 — Post-fix shadow evidence collection
Status: IN_PROGRESS

Proof:
- TP/SL cap issue was previously corrected
- simulator path was previously repaired
- shadow manager now runs again
- uniqueness protection is installed but not fully exercised

What remains:
- collect fresh post-fix rows
- evaluate unique trades only
- separate true no-signal conditions from operational failures

---

## 3) OPEN

### Signal scarcity / no signals today
Status: OPEN

Known likely contributors from logs:
- `score<65`
- `vetoed_by_H1`
- `adx_regime_block`
- `no_signal`

Not yet proven:
- whether scarcity is mainly threshold-related
- whether H1 veto is overly restrictive
- whether current market regime is simply producing weak setups

Next step after current integrity proof:
- perform focused audit of today/recent blocked candidates by reason bucket

---

### OPS-005 — Closer network failures
Status: OPEN

Proof:
- historical closer/network errors exist in logs
- not yet proven whether they currently affect result tracking after recent fixes

Next step:
- inspect recent closer behavior separately after shadow scheduling proof stabilizes

---

## 4) BLOCKED / NOT READY

### Full duplicate-source resolution upstream
Status: BLOCKED

Reason:
- not safe to change watcher/scorer/publisher dedup yet
- storage-boundary proof must be exercised first
- changing upstream now would hide evidence and mix causes

---

## 5) NEXT PROOF ORDER

1. Verify scheduled shadow manager runs from cron
2. Verify heartbeat continuity improves
3. Wait for active signal and observe `ensure_shadow_row()` path
4. Reassess duplicate evidence quality
5. Audit signal scarcity / accuracy only after integrity proof is current

---

## 6) RULES FOR UPDATING THIS FILE

1. Never mark FIXED without log or command proof.
2. Distinguish:
   - installed
   - proven
   - fully exercised
3. Do not collapse operational fixes into strategy fixes.
4. If a fix is partial, say exactly what remains unproven.
5. Keep next-proof order explicit.

---

## 7) CHANGE LOG

### 2026-04-07
- Created canonical remaining-fixes map.
- Recorded TP/SL cap math as proven fixed.
- Recorded simulator and replay-rule fixes as proven fixed.
- Captured operational errors from logs.
- Captured current strategy validation blockers and unknowns.

### 2026-04-08
- Marked cron Python execution issue fixed.
- Marked shadow manager env/bootstrap and scheduling fixed.
- Recorded storage-boundary uniqueness hardening as installed and partially proven.
- Added explicit next-proof order before any signal-accuracy tuning.
