# Heartbeat Observability Correction — Closure Verification Record

**Marker:** BOTA_HEARTBEAT_OBSERVABILITY_CORRECTION_V32_2026_07_12
**Generated:** 2026-07-12
**Branch:** fix/heartbeat-observability-20260712
**Implementation commit:** 6cdfc7f97090b4bfae9ba0b015940205778d9ed6

## Closure Facts

[proven] Branch base: fa289ad3f7b6ff430f13609950e5af341aee2e9d (main)
[proven] Implementation commit: 6cdfc7f97090b4bfae9ba0b015940205778d9ed6
[proven] Commit scope: tools/heartbeat.sh, tests/test_heartbeat.sh only
[proven] tools/heartbeat.sh SHA-256: 8226a935c30be8a3484ed20bf3e79192d9fb020f6dc827e4e89af3c23a2fe202
[proven] tests/test_heartbeat.sh SHA-256: cad581f326ef5b4fbf7c1f26065cb43de3abc70cf9b4a573d7ff5bc4647e81c1
[proven] Offline validation: 29 test cases, 108 assertions, 108 passed, 0 failed
[proven] Real network attempts: 0
[proven] Secret-safety scans: passed
[proven] Bash syntax validation: passed
[proven] CI Security Scan on commit 6cdfc7f: completed/success (18s)
[proven] Local HEAD == Remote HEAD: 6cdfc7f97090b4bfae9ba0b015940205778d9ed6
[proven] Production checkout (main, fa289ad): unchanged
[proven] Historical-replay worktree: unchanged
[proven] No live Telegram test run
[proven] Corrected heartbeat NOT yet deployed
[proven] No documentation or state files entered the implementation commit
[proven] Strategy, H1, ADX, thresholds, pairs, cron, OANDA, Supabase: unchanged
[proven] No force push

## Deployment Gate (all must be satisfied before deployment)

1. Documentation-and-state closure commit (this increment)
2. Separately reviewed deployment plan
3. Explicit deployment approval
4. Post-deployment local verification
5. Separately approved live Telegram validation if required

## Handoff Pack Output (production BotA root — read-only reference)

=== BOTA HANDOFF PACK ===

--- GIT ---
main
fa289ad
?? audits/bota_live_status_20260519_013807.txt
?? state/bota_shipmode_crontab.txt
?? state/daily_pulse_sent_2026-05-27.ok
?? state/daily_summary_sent_2026-05-19.ok
?? state/daily_summary_sent_2026-05-22.ok
?? state/daily_summary_sent_2026-05-23.ok
?? state/daily_summary_sent_2026-05-24.ok
?? state/daily_summary_sent_2026-05-25.ok
?? state/daily_summary_sent_2026-05-26.ok
?? state/daily_summary_sent_2026-05-27.ok
?? state/daily_summary_sent_2026-05-29.ok
?? state/daily_summary_sent_2026-05-30.ok
?? state/daily_summary_sent_2026-06-01.ok
?? state/daily_summary_sent_2026-06-02.ok
?? state/daily_summary_sent_2026-06-09.ok
?? state/daily_summary_sent_2026-06-10.ok
?? state/daily_summary_sent_2026-06-11.ok
?? state/daily_summary_sent_2026-06-12.ok
?? state/daily_summary_sent_2026-06-13.ok
?? state/daily_summary_sent_2026-06-14.ok
?? state/daily_summary_sent_2026-06-15.ok
?? state/daily_summary_sent_2026-06-16.ok
?? state/daily_summary_sent_2026-06-17.ok
?? state/daily_summary_sent_2026-06-19.ok
?? state/daily_summary_sent_2026-06-20.ok
?? state/daily_summary_sent_2026-06-21.ok
?? state/daily_summary_sent_2026-07-06.ok
?? state/daily_summary_sent_2026-07-07.ok
?? state/daily_summary_sent_2026-07-08.ok
?? state/daily_summary_sent_2026-07-09.ok
?? state/daily_summary_sent_2026-07-10.ok
?? state/daily_summary_sent_2026-07-11.ok
?? state/oanda_curl_default.json
?? state/oanda_curl_insecure.json
?? state/pulse_enabled.flag
?? state/yahoo_default.json
?? state/yahoo_insecure.json

--- HANDOFF STATUS ---
HANDOFF_STATUS=WARN
WARN=git_worktree_dirty
WARN=state_json_older_than_cache_or_indicators

--- RUNTIME HEALTH (state/runtime_health.json) ---
bot_mode              = DEGRADED
last_supervisor_run   = 2026-07-12T14:00:01.526492Z
crond_pid             = 5027
watcher_log_age_min   = 15
updater_log_age_min   = 0
shadow_log_age_min    = 15
eurusd_m15_cache_age  = 151min
gbpusd_m15_cache_age  = 0min
eurusd_h1_cache_age   = 151min
gbpusd_h1_cache_age   = 0min
failure_reasons       = eurusd_m15_stale:151min|eurusd_h1_stale:151min|server_clock_unavailable
last_healthy_utc      = 2026-07-09T15:30:00.846556Z
last_degraded_utc     = 2026-07-12T14:00:01.526492Z
last_degraded_reason  = eurusd_m15_stale:151min|eurusd_h1_stale:151min|server_clock_unavailable

--- STATE SNAPSHOT (state/STATE.json) ---
{
  "_meta": {
    "schema_version": "1.1",
    "project": "BotA",
    "repo": "Ciupanezulflipper/BotA_Prod_2025_11",
    "supabase_project": "ozgkeslgjqbqfewojnmr",
    "runtime": "Termux Android arm64",
    "last_updated": "2026-05-27T11:17:02Z",
    "updated_by": "claude-sonnet-4-6",
    "session_id": "2026-05-27 Step 6 daily pulse wrapper + first private live send + layout cleanup"
  },
  "git": {
    "current_branch": "main",
    "latest_commit_hash": "7040b22",
    "dirty_tracked_files_audit": {
      "tools/data_fetch_candles.sh": "INTENTIONAL - COMMITTED ad704fd/acb7e2e",
      "tools/market_open.sh": "INTENTIONAL - COMMITTED acb7e2e",
      "tools/build_indicators.py": "SUSPICIOUS - RESTORED TO HEAD",
      "tools/scoring_engine.sh": "SUSPICIOUS - RESTORED TO HEAD",
      "tools/signal_watcher_pro.sh": "SUSPICIOUS - RESTORED TO HEAD",
      "tools/supabase_publish.py": "SUSPICIOUS - RESTORED TO HEAD"
    },
    "state_json_git_blocked": false
  },
  "infrastructure": {
    "crond_running": true,
    "termux_boot_script_exists": true,
    "boot_proof_last_entry": "2026-04-24T04:30:03+1000",
    "stale_lock_fix_installed": true,
    "deadman_alert_installed": true,
    "deadman_threshold_min": 60,
    "deadman_flag_path": "logs/state/deadman.flag",
    "supabase_env_fix_installed": true,
    "supabase_env_source": "config/strategy.env"
  },
  "pipeline": {
    "watcher": {
      "scope_pairs": [
        "EURUSD",
        "GBPUSD"
      ],
      "scope_timeframes": [
        "M15"
      ],
      "scope_locked": true,
      "scope_unlock_criteria": "15+ shadow_adx non-HOLD entries with score_partial >= 52, not >80% one-sided, D1 aligned",
      "stale_lock_fix": "installed - removes lockfile older than 900s",
      "last_known_outcome": "FILTER REJECT - market regime / no_signal or H1_trend_neutral",
      "last_known_blocker": "M15 no_signal most cycles; occasional near-signal EURUSD cycles vetoed by H1_trend_neutral. No infrastructure blocker proven."
    },
    "updater": {
      "scope_pairs": [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "EURJPY",
        "XAUUSD"
      ],
      "scope_timeframes": [
        "M15",
        "H1",
        "H4",
        "D1"
      ],
      "yahoo_429_exit3_installed": true,
      "updater_skip_retry_rc3_installed": true,
      "d1_refresh_via_updater": [
        "EURUSD",
        "GBPUSD"
      ],
      "d1_refresh_via_standalone": [
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "XAUUSD"
      ],
      "d1_scope_note": "indicators_updater.sh hardcoded to EURUSD/GBPUSD only. refresh_d1_cache.sh covers 4 pairs.",
      "last_run_outcome": "fetch_fail_count=0 build_fail_count=0",
      "last_run_utc": "2026-04-24"
    },
    "shadow_manager": {
      "cron_schedule": "2,17,32,47 * * * *",
      "supabase_env_fix_installed": true,
      "schema_check_last_status": "PASS - 30 required columns verified",
      "last_heartbeat_status": "OK - 1 active signal",
      "policies_running": [
        "STATIC_MIRROR",
        "BE_1.0R"
      ],
      "active_signals_supabase": 1,
      "prior_error_root_cause": "SUPABASE_URL/KEY not sourced in cron - NOT missing columns. Verified via MCP."
    },
    "heartbeat": {
      "cron_schedule": "0 * * * *",
      "deadman_alert_installed": true,
      "telegram_token_source": "config/tele.env",
      "last_deadman_alert_utc": null,
      "last_recovery_alert_utc": null
    },
    "d1_cache": {
      "eurusd_trend": "BUY",
      "eurusd_ema9": 1.17342,
      "eurusd_ema21": 1.1691,
      "gbpusd_trend": "BUY",
      "gbpusd_ema9": 1.34929,
      "gbpusd_ema21": 1.34419,
      "last_refresh_utc": "2026-04-24",
      "usdjpy_d1_note": "Refreshed 2026-04-24 via updater build OK.",
      "xauusd_d1_note": "Refreshed 2026-04-21 - was stale since 2026-04-09"
    }
  },
  "market_data": {
    "oanda_last_http_status": 200,
    "oanda_last_response_time_s": null,
    "yahoo_last_http_status": null,
    "network_state": "OPERATIONAL",
    "network_state_reason": "OANDA fetch/build OK after reboot proof; watcher/updater/shadow logs advancing.",
    "eurusd_m15_last_candle_utc": null,
    "gbpusd_m15_last_candle_utc": null
  },
  "scoring": {
    "eurusd_m15_direction": "HOLD",
    "eurusd_m15_score": 0.0,
    "eurusd_m15_blocker": "no_signal|phase=Open",
    "gbpusd_m15_direction": "HOLD",
    "gbpusd_m15_score": 0.0,
    "gbpusd_m15_blocker": "no_signal|phase=Open",
    "filter_score_min": 65,
    "telegram_min_score": 70,
    "adx_hard_gate": 20.0,
    "current_alert_silence_reason": "Market regime - M15 no_signal most cycles; near-signal EURUSD cycles vetoed by H1_trend_neutral. macro6 short-circuit is secondary, not primary.",
    "scorer_is_broken": false,
    "scorer_pass_proof": "Structured scorer/fusion output is present; watcher reached 68.70-76.10 EURUSD near-signal cycles before H1 neutral veto."
  },
  "market_open_contract": {
    "fix_installed": true,
    "prior_behavior": "Emitted descriptive strings e.g. Closed (Asian session 00:00-07:00 UTC)",
    "current_behavior": "Emits exact Open or Closed only",
    "root_cause_of_phase_unknown": "scoring_engine.sh lines 203-209 only accepted exact Open/Closed. Descriptive strings caused PHASE=Unknown.",
    "fix_verified": true,
    "fix_proof": "After fix: scorer returned reasons=market phase Closed with provider=scoring_engine_market"
  },
  "usdjpy_status": {
    "technical_ready": true,
    "live_scope_approved": false,
    "technical_proof": "OANDA M15/H1/H4/D1 fetch/build OK after reboot proof.",
    "fusion_rejection_reason": "Not approved for live watcher scope.",
    "d1_trend": "BUY as of 2026-04-24 updater build",
    "decision": "NOT approved for live watcher. Technical validation != live approval.",
    "do_not_add_to_watcher": true
  },
  "shadow_adx_experiment": {
    "logger_installed": true,
    "shadow_gate_threshold": 15.0,
    "log_path": "logs/shadow_adx_scoring.jsonl",
    "last_proven_entry": {
      "pair": "EURUSD",
      "adx": 18.6,
      "direction_pre_gate": "BUY",
      "score_partial_pre_gate": 51.6,
      "entry": 1.17905,
      "sl": 1.17832,
      "tp": 1.18052,
      "d1_trend": "BUY",
      "timestamp": "2026-04-20T23:09:00Z"
    },
    "promotion_criteria": {
      "min_entries_non_hold": 15,
      "min_score_partial": 52.0,
      "max_one_sided_pct": 80,
      "d1_alignment_required": true,
      "all_criteria_met": false
    },
    "key_insight": "score_partial=51.6 below live filter threshold. Context preservation improves observability but will NOT restore alerts alone."
  },
  "supabase": {
    "project_id": "ozgkeslgjqbqfewojnmr",
    "region": "eu-west-1",
    "signals_active_count": 1,
    "shadow_log_row_count": 2,
    "shadow_log_schema_verified": true,
    "schema_verification_method": "information_schema.columns via MCP - all 30 columns confirmed present",
    "false_diagnosis_rejected": "Missing last_candle_ts_processed diagnosis was falsified by direct MCP check."
  },
  "reboot_proof": {
    "proven_at": "2026-04-24",
    "result": "PASS",
    "crond_pid_after_reboot": 29694,
    "watcher_log_advanced": "04:30",
    "updater_log_advanced": "04:29",
    "shadow_log_advanced": "04:45",
    "manual_intervention_required": false,
    "caveat": "One real-world reboot proven. Not guaranteed for all future Android/Termux conditions.",
    "second_reboot_proven_at": "2026-04-24",
    "second_reboot_crond_pid": 24859,
    "autonomous_supervisor_tick_proven": true,
    "supervisor_tick_utc": "2026-04-24T05:45:02Z"
  },
  "open_issues": [
    {
      "id": "news-on-disabled",
      "title": "NEWS_ON unset - fusion macro path short-circuits to macro6=3/provider=off",
      "status": "open",
      "facts": [
        "news_sentiment.py is implemented and working - direct CLI output returned macro6=0 via RSS for EURUSD and GBPUSD",
        "NEWS_ON=0/unset causes m15_h1_fusion.sh lines 109-112 to bypass news_sentiment.py and inject macro6=3/provider=off",
        "macro6=3 appears in filter_reasons but is not the primary signal blocker",
        "primary active veto on near-signal cycles is H1_trend_neutral",
        "latest direct H1 context proved ema9<ema21 and RSI<50 on both EURUSD and GBPUSD H1"
      ],
      "decision": "No config change approved yet. Enable NEWS_ON=1 only after a supportive H1 context and a near-signal cycle are observed.",
      "do_not_change": [
        "NEWS_ON",
        "macro6 threshold",
        "H1 fusion logic"
      ]
    },
    {
      "id": "suspicious-4-files-provenance",
      "title": "4 files had large unaudited diffs - restored to HEAD, provenance unknown",
      "files": [
        "tools/build_indicators.py",
        "tools/scoring_engine.sh",
        "tools/signal_watcher_pro.sh",
        "tools/supabase_publish.py"
      ],
      "status": "deferred",
      "next_step": "Audit in separate session with git log --follow per file"
    },
    {
      "id": "signal-mutation-auditability",
      "title": "No audit trail for signal status mutations — March 19 source permanently unresolvable",
      "status": "open",
      "priority": "next_engineering_session",
      "proposed_fix": "Add closed_source, closed_by, close_reason columns to signals table, or implement append-only mutation log",
      "why": "Without this, any future batch close event cannot be attributed to an actor or tool",
      "constraint": "Do not implement before commercial validation is underway — schema change requires ProfitLab coordination"
    }
  ],
  "resolved": [
    {
      "id": "hotfix-pr-3-merged",
      "title": "hotfix/rate-limit-deadman-20260421 merged to main",
      "resolved_at": "2026-04-23",
      "proof": "main HEAD 7c3a18d; STATE.json schema_version 1.1 on main; handoff_pack.sh runs from main",
      "do_not_reopen": true
    },
    {
      "id": "stale-lock",
      "title": "Stale watcher.lock blocked scans since 2026-04-14",
      "resolved_at": "2026-04-19",
      "file": "tools/signal_watcher_pro.sh",
      "do_not_reopen": true
    },
    {
      "id": "yahoo-429-storm",
      "title": "Yahoo fallback retry storm",
      "resolved_at": "2026-04-21",
      "files": [
        "tools/data_fetch_candles.sh",
        "tools/indicators_updater.sh"
      ],
      "do_not_reopen": true
    },
    {
      "id": "deadman-missing",
      "title": "No alert during 5-day pipeline silence",
      "resolved_at": "2026-04-21",
      "file": "tools/heartbeat.sh",
      "do_not_reopen": true
    },
    {
      "id": "supabase-env-shadow",
      "title": "Shadow manager cron schema check failed - env not sourced",
      "resolved_at": "2026-04-21",
      "file": "tools/run_shadow_manager.sh",
      "root_cause": "SUPABASE_URL/KEY in config/strategy.env not .env",
      "do_not_reopen": true
    },
    {
      "id": "phase-unknown-bug",
      "title": "phase=Unknown on every off-hours scorer run",
      "resolved_at": "2026-04-21",
      "file": "tools/market_open.sh",
      "root_cause": "market_open.sh emitted descriptive strings; scorer only accepted exact Open/Closed",
      "do_not_reopen": true
    },
    {
      "id": "stale-candles-2026-04-14",
      "title": "M15 cache stale since 2026-04-14",
      "resolved_at": "2026-04-21",
      "root_cause": "Stale lock + Yahoo DNS failures during ship connectivity outage",
      "do_not_reopen": true
    }
  ],
  "decisions": [
    {
      "id": "watcher-scope-locked",
      "decision": "EURUSD GBPUSD M15 only. No changes until shadow experiment criteria met.",
      "decided_at": "2026-04-21",
      "do_not_change": [
        "PAIRS",
        "TIMEFRAMES",
        "FILTER_SCORE_MIN",
        "TELEGRAM_MIN_SCORE",
        "ADX_GATE"
      ]
    },
    {
      "id": "usdjpy-not-live",
      "decision": "USDJPY technically validated, NOT approved for live scope.",
      "decided_at": "2026-04-21"
    },
    {
      "id": "alerts-csv-excluded",
      "decision": "alerts.csv excluded from all evidence chains. Proven contaminated.",
      "decided_at": "2026-04-06",
      "do_not_reopen": true
    },
    {
      "id": "oanda-primary",
      "decision": "OANDA primary. Yahoo fallback only. BotA and Forex Profit Lab never merged.",
      "decided_at": "2026-03-09",
      "do_not_reopen": true
    },
    {
      "id": "no-strategy-changes-until-data",
      "decision": "No ADX gate, threshold, or scope changes until shadow data justifies it. Current silence = market regime.",
      "decided_at": "2026-04-21"
    },
    {
      "id": "state-json-canonical",
      "decision": "state/STATE.json is single source of truth. One file. No hybrid schemas. Updated every session.",
      "decided_at": "2026-04-22"
    }
  ],
  "product_message_v1": {
    "market_pulse": {
      "status": "step_6_wrapper_live_private",
      "shadow_mode_working": true,
      "send_mode_working": true,
      "step_5_private_send_passed": true,
      "step_5_commit": "274b0d3",
      "step_5_tag": "step-5-private-send-confirmed-2026-05-27",
      "step_6_wrapper_commit": "6aa985e",
      "step_6_wrapper_tag": "step-6-wrapper-gates-2026-05-27",
      "step_6_layout_cleanup_commit": "65d1137",
      "step_6_first_private_send_passed": true,
      "step_6_live_send_exit_code": 0,
      "step_6_telegram_sent": true,
      "step_6_supabase_published": false,
      "step_6_dedup_file_created": "state/daily_pulse_sent_2026-05-27.ok",
      "step_6_confirmed_at": "2026-05-27",
      "cron_active": false,
      "main_channel_rollout_approved": false,
      "private_sends_confirmed": 1,
      "private_sends_required_before_rollout": 3,
      "step_6_next": "2 more confirmed private daily sends, then request cron/main channel decision",
      "macro6_neutral_bug_fixed": true,
      "contains_entry_sl_tp": false,
      "contains_disclaimer": true,
      "production_trading_changed": false,
      "strategy_changed": false,
      "h1_changed": false,
      "thresholds_changed": false,
      "cron_changed": false,
      "supabase_publish_market_pulse": false,
      "profitlab_signal_behavior_changed": false
    }
  },
  "profitlab_signals": {
    "total_closed": 42,
    "dashboard_win_rate_pct": 38,
    "dashboard_note": "38% is contaminated by March 13 bulk close. Do not use for commercial claims.",
    "march13_bulk_close": {
      "count": 24,
      "classification": "manual_or_semi_manual_batch_close",
      "root_cause": "live execution of signal_closer.py — proven via log sequence",
      "ids_excluded": 24
    },
    "march19_batch": {
      "count": 4,
      "closed_at_utc": "2026-03-19T19:15:13 to 19:15:15",
      "pattern": "4 signals closed in 1.5 seconds, all at exactly +60.0 pips",
      "signal_closer_log_finding": "signal_closer.py ran at 19:16 UTC, found 2 active signals, closed zero — does not explain the 19:15 batch",
      "classification": "UNPROVEN — source unknown. signal_closer.py 19:16 run ruled out. Shadow manager ruled out. No audit metadata in DB to determine actor.",
      "status": "confirmed_excluded",
      "ids_confirmed": [
        "956ecc3a-f9bd-41e1-bf00-6f2bb3024d2e",
        "f0b449d1-7e62-4683-82a3-a6b99bd245ae",
        "18914aa4-4251-47d3-a1a9-f50b927ec000",
        "f8255de7-b11a-4d61-b8a6-ddb49e9ea580"
      ],
      "ids_confirmed_by": "Query 1A — MCP Supabase direct 2026-04-29. Exactly 4 rows returned matching closed_at window + result_pips=60.0. IDs match march19_ids_to_exclude.",
      "source_unresolvable": true,
      "source_unresolvable_note": "Would require Supabase pgaudit extension or ProfitLab server logs from 2026-03-19 19:15 UTC"
    },
    "null_closed_at_signals": {
      "count": 2,
      "note": "result_pips set but closed_at is NULL — data integrity issue, excluded from baseline"
    },
    "provisional_baseline_after_excluding_march13": {
      "baseline_status": "SUPERSEDED — see clean_baseline_after_excluding_both_batches",
      "superseded_by": "clean_baseline_after_excluding_both_batches",
      "method": "exclude_24_proven_march13_ids_only",
      "caveat": "Included March 19 batch (4 signals at +60.0 pips each). Inflated by contamination. Superseded 2026-04-29.",
      "organic_total": 18,
      "winners": 9,
      "losers": 9,
      "win_rate_pct": 50.0,
      "avg_win_pips": 46.7,
      "avg_loss_pips": -24.6,
      "net_pips": 198.1,
      "expectancy_pips": 11.0,
      "profit_factor": 1.89,
      "rr_ratio": 1.9,
      "frozen_at": "2026-04-24",
      "do_not_use_for_commercial_claims": true
    },
    "clean_baseline_after_excluding_both_batches": {
      "baseline_status": "final",
      "method": "exclude_28_ids_march13_24_plus_march19_4",
      "excluded_march13_count": 24,
      "excluded_march19_count": 4,
      "excluded_total_confirmed": 28,
      "clean_total": 14,
      "winners": 5,
      "losers": 9,
      "win_rate_pct": 35.7,
      "avg_win_pips": 36.0,
      "avg_loss_pips": -24.6,
      "net_pips": -41.9,
      "expectancy_pips": -3.0,
      "profit_factor": 0.81,
      "frozen_at": "2026-04-29",
      "computed_by": "Query 1B — MCP Supabase direct 2026-04-29",
      "do_not_use_for_commercial_claims": true,
      "note": "Net negative. March 19 batch was heavily inflating the provisional baseline (+198.1 pips → -41.9 pips after exclusion). 14 signals is statistically insufficient for any strategy conclusion."
    }
  },
  "git_auth": {
    "bota_remote_protocol": "SSH",
    "remote_origin_url": "git@github.com:Ciupanezulflipper/BotA_Prod_2025_11.git",
    "ssh_key_path": "~/.ssh/id_ed25519",
    "ssh_key_auth_proven": true,
    "git_fetch_over_ssh_passed": true,
    "git_push_over_ssh_passed": true,
    "pat_primary_for_normal_git": false,
    "credential_helper_global": "store",
    "git_credentials_store_cleaned": true,
    "pat_revoked": "UNPROVEN",
    "migrated_at": "2026-04-26",
    "note": "BotA remote now uses SSH for normal git pull/push. Global credential.helper=store still exists, but BotA remote is SSH. PAT is no longer the primary git path for BotA."
  },
  "observability_v4_2026_07_10": {
    "claim_status": "proven",
    "status": "resolved_and_live_verified",
    "marker": "BOTA_OBSERVABILITY_V4_2026_07_10",
    "preserved_at_utc": "2026-07-10T17:14:24.939195+00:00",
    "watcher_path": "tools/signal_watcher_pro.sh",
    "watcher_sha256": "b8a3adf46582e3a69d5b22d12a4da070bc8be2ceff76a4aa99e9d6c96544a9ef",
    "active_pairs": [
      "EURUSD",
      "GBPUSD"
    ],
    "active_timeframes": [
      "M15"
    ],
    "decision_journal": "logs/alerts.csv",
    "journal_before_rejection_and_delivery_gates": true,
    "delivery_hash_compare_read_only_before_send": true,
    "delivery_hash_mark_after_successful_real_telegram_send": true,
    "delivery_hash_identity": [
      "pair",
      "tf",
      "direction",
      "score",
      "entry",
      "sl",
      "tp"
    ],
    "existing_hashes_reset": false,
    "existing_last_sent_reset": false,
    "strategy_changed": false,
    "h1_logic_changed": false,
    "adx_logic_changed": false,
    "thresholds_changed": false,
    "pairs_changed": false,
    "timeframes_changed": false,
    "cron_changed": false,
    "natural_cycle_proof": {
      "passed": true,
      "alerts_lines_before": 1590,
      "alerts_lines_after": 1592,
      "row_delta": 2,
      "eurusd_row": {
        "direction": "HOLD",
        "score": 0.0,
        "confidence": 40.0,
        "rejected": true,
        "reason": "no_signal|phase=Open"
      },
      "gbpusd_row": {
        "direction": "HOLD",
        "score": 0.0,
        "confidence": 40.0,
        "rejected": true,
        "reason": "no_signal|phase=Open"
      },
      "delivery_hashes_unchanged": true,
      "last_sent_files_unchanged": true,
      "telegram_sent": false
    },
    "historical_june_outage": {
      "runtime_or_scheduling_failure": "proven",
      "post_recovery_rejected_hold_state": "proven",
      "valid_alert_suppressed": "not_proven",
      "fully_reconstruct_old_omitted_decisions": false
    },
    "next_action": "Generate and verify handoff pack, then review exact git diff before commit and push."
  }
}

--- LOCKED DECISIONS (tail) ---
  - SUPABASE_SERVICE_KEY
  - TELEGRAM_BOT_TOKEN
- Deferred:
  - lower-priority/read-only provider keys
- Do not change:
  - do not weaken .gitleaks.toml just to get green CI

## Product Market Pulse send gate — 2026-05-27
- Status: LOCKED
- Decisions:
  1. `--send` mode requires `--chat-id` to be passed explicitly on the command line at all times.
     Do not default to `TELEGRAM_CHAT_ID` env var for Step 5 or any early rollout phase.
  2. Market Pulse must not publish to ProfitLab/Supabase `signals` table.
     `supabase_published=false` is mandatory for all Market Pulse message types.
  3. Daily Market Pulse must go to private test chat first.
     Require 3 confirmed successful private daily sends before main channel or cron rollout.
  4. Main BotA channel rollout requires a separate explicit approval step.
     Do not widen send scope to the main channel without that approval.
  5. Cron scheduling for Market Pulse requires a separate explicit approval step after private proof.
     Do not add cron for any Market Pulse send without that approval.
- Proof:
  - Step 5 commit `274b0d3`, tag `step-5-private-send-confirmed-2026-05-27`
  - Step 6 commit `6aa985e`, tag `step-6-wrapper-gates-2026-05-27`
  - Step 6A layout commit `65d1137`
  - First private wrapper send: `LIVE_SEND_EXIT_CODE=0`, `telegram_sent=True`, `supabase_published=False`

---

## 2026-07-10 — Watcher decision journaling and delivery dedup

<!-- BOTA_OBSERVABILITY_V4_2026_07_10 -->

- [proven] Decision: `logs/alerts.csv` is the completed-decision journal and must be written before rejection or delivery exits.
- [proven] Decision: Telegram/Supabase delivery dedup must remain separate from decision journaling.
- [proven] Decision: `last_hash_<PAIR>_<TF>.txt` represents successful real Telegram delivery, not merely candidate evaluation.
- [proven] Decision: delivery-hash comparison is read-only before send; the hash is marked only after successful real Telegram delivery.
- [proven] Decision: preserve the existing seven-field hash identity for this repair.
- [proven] Decision: do not reset historical delivery hashes or cooldown files.
- [proven] Decision: do not modify strategy, H1 veto, ADX handling, thresholds, watched pairs/timeframe, RR rules, Telegram tiers, or cron cadence in this repair.
- [inferred] Separate Supabase-specific delivery retry state may be evaluated later, but it is outside this approved observability repair.

--- RESOLVED (tail) ---

### Step 5 private Telegram Market Pulse send
- Status: RESOLVED
- What was proven:
  - `tools/product_message_v1.py --send --chat-id <TEST_CHAT_ID>` delivered message to private test chat.
  - `telegram_sent=True` confirmed in log and stdout.
  - `supabase_published=False` confirmed.
  - Shadow mode continues working: `telegram_sent=False`, `supabase_published=False`.
  - macro6=3 neutral/default no longer displayed as "macro filter active".
  - Market Pulse contains no entry, SL, or TP.
  - Market Pulse disclaimer present.
- Commit: `274b0d3`
- Tag: `step-5-private-send-confirmed-2026-05-27`
- Branch: `main`, pushed to `origin/main`.
- Production trading behavior changed: NO.
- Strategy changed: NO.
- H1 logic changed: NO.
- Thresholds changed: NO.
- Cron changed: NO.
- Supabase publish for Market Pulse: NO (remains false).
- ProfitLab executable signal behavior: UNCHANGED.

---

## 2026-07-10 — Watcher pre-journal dedup observability defect

<!-- BOTA_OBSERVABILITY_V4_2026_07_10 -->

- Status: RESOLVED
- [proven] Root cause: content dedup executed before `alerts.csv` journaling and wrote hash state before confirmed Telegram delivery.
- [proven] Fix: journal every completed parsed decision before rejection and Telegram delivery gates.
- [proven] Fix: split delivery hash calculation, read-only comparison, and post-success marking.
- [proven] Fix: update delivery hash only after successful real Telegram send.
- [proven] Static validation: PASS.
- [proven] Atomic deployment: PASS.
- [proven] Natural cron-cycle validation: PASS.
- [proven] Natural proof wrote two rejected HOLD rows while preserving both delivery hashes and both `last_sent` files.
- [proven] Installed watcher SHA-256: `b8a3adf46582e3a69d5b22d12a4da070bc8be2ceff76a4aa99e9d6c96544a9ef`.
- [proven] Strategy and production selection rules changed: NO.
- [not proven] Whether any valid signal was missed during the historical June outage remains unresolved.

--- CONTINUITY (tail) ---

- [proven] `tools/signal_watcher_pro.sh` was replaced atomically with the validated Observability V4 implementation.
- [proven] Installed watcher SHA-256 is `b8a3adf46582e3a69d5b22d12a4da070bc8be2ceff76a4aa99e9d6c96544a9ef`.
- [proven] Every completed parsed decision is now appended to `logs/alerts.csv` before rejection, score, tier, cooldown, and delivery-dedup exits.
- [proven] Delivery dedup is checked only after rejection, score, tier, and cooldown gates.
- [proven] Delivery hash state is written only after a successful real Telegram send.
- [proven] Existing hash identity remains `pair|tf|direction|score|entry|sl|tp`.
- [proven] Existing `last_hash_*` and `last_sent_*` files were not reset during deployment.
- [proven] Strategy, H1 logic, ADX rules, score thresholds, pairs, timeframe, risk rules, Telegram tiers, cooldown duration, cron cadence, and Supabase eligibility were unchanged.

### Static proof

- [proven] Candidate transformation passed.
- [proven] `bash -n` passed.
- [proven] Structural order validation passed.
- [proven] Semantic static validation passed.
- [proven] Atomic deployment passed without rollback.

### Natural cron-cycle proof

- [proven] A natural scheduled watcher cycle advanced `logs/alerts.csv` from 1590 to 1592 rows.
- [proven] Exactly two new rows were written: EURUSD M15 HOLD and GBPUSD M15 HOLD.
- [proven] Both rows had score `0.00`, confidence `40.00`, provider `engine_A3`, rejection status `true`, and reason `no_signal|phase=Open`.
- [proven] EURUSD and GBPUSD delivery-hash contents and mtimes remained unchanged.
- [proven] EURUSD and GBPUSD `last_sent` contents and mtimes remained unchanged.
- [proven] No Telegram delivery occurred for the rejected HOLD rows.
- [proven] `NATURAL_CYCLE_PROOF_PASS=YES`.

### Current interpretation

- [proven] BotA now preserves evidence distinguishing “no valid setup” from runtime or delivery failure.
- [proven] The 2026-07-10 live snapshot had no alert-grade setup inside the active watcher universe.
- [not proven] Historical market decisions omitted by the old pre-journal dedup cannot be reconstructed completely.
- [inferred] Future signal-drought investigations can now use `alerts.csv` as the completed-decision journal.

### Scope lock

- [proven] This was an observability and delivery-state correction only.
- [proven] No strategy-frequency change was approved.
- [proven] Do not loosen H1 veto, ADX gates, score thresholds, or watcher scope based only on signal-drought frustration.

--- CURRENT WATCHER SCOPE FROM STATE ---
pairs= ['EURUSD', 'GBPUSD']
timeframes= ['M15']

--- error.log tail ---
📡 API: 352/800 credits (44.0%) 🟢
2026-07-12 15:59:57 [indicators] Yahoo chart candles loaded: 500 rows
[FETCH] trying OANDA: instrument=USD_JPY gran=M15
[FETCH] OANDA OK
[FETCH] legacy cache NOT updated (tf=M15)
[FETCH] OK provider=oanda wrote: /data/data/com.termux/files/home/BotA/cache/USDJPY_M15.json
[FETCH] OK wrote: /data/data/com.termux/files/home/BotA/data/candles/USDJPY_M15.csv
📡 API: 353/800 credits (44.1%) 🟢
2026-07-12 15:59:59 [indicators] Yahoo chart candles loaded: 500 rows
[FETCH] trying OANDA: instrument=USD_JPY gran=H1
[FETCH] OANDA OK
[FETCH] legacy cache updated: /data/data/com.termux/files/home/BotA/cache/USDJPY.json
[FETCH] OK provider=oanda wrote: /data/data/com.termux/files/home/BotA/cache/USDJPY_H1.json
[FETCH] OK wrote: /data/data/com.termux/files/home/BotA/data/candles/USDJPY_H1.csv
📡 API: 354/800 credits (44.2%) 🟢
2026-07-12 16:00:01 [indicators] Yahoo chart candles loaded: 500 rows
[FETCH] trying OANDA: instrument=USD_JPY gran=H4
[FETCH] OANDA OK
[FETCH] legacy cache NOT updated (tf=H4)
[FETCH] OK provider=oanda wrote: /data/data/com.termux/files/home/BotA/cache/USDJPY_H4.json
[FETCH] OK wrote: /data/data/com.termux/files/home/BotA/data/candles/USDJPY_H4.csv
📡 API: 355/800 credits (44.4%) 🟢
2026-07-12 16:00:03 [indicators] Yahoo chart candles loaded: 500 rows
[FETCH] trying OANDA: instrument=USD_JPY gran=D
[FETCH] OANDA OK
[FETCH] legacy cache NOT updated (tf=D1)
[FETCH] OK provider=oanda wrote: /data/data/com.termux/files/home/BotA/cache/USDJPY_D1.json
[FETCH] OK wrote: /data/data/com.termux/files/home/BotA/data/candles/USDJPY_D1.csv
📡 API: 356/800 credits (44.5%) 🟢
2026-07-12 16:00:05 [indicators] Yahoo chart candles loaded: 500 rows

--- D1 cache mtimes ---
-rw-------. 1 u0_a414 u0_a414 169 2026-07-12 16:00 cache/d1_trend_EURUSD.json
-rw-------. 1 u0_a414 u0_a414 169 2026-07-12 16:00 cache/d1_trend_GBPUSD.json
-rw-------. 1 u0_a414 u0_a414 168 2026-04-22 02:16 cache/d1_trend_USDJPY.json
-rw-------. 1 u0_a414 u0_a414 167 2026-04-22 02:16 cache/d1_trend_XAUUSD.json

--- indicator mtimes (latest 10) ---
2026-07-12 16:00 cache/indicators_USDJPY_H4.json
2026-07-12 16:00 cache/indicators_USDJPY_H1.json
2026-07-12 16:00 cache/indicators_USDJPY_D1.json
2026-07-12 15:59 cache/indicators_USDJPY_M15.json
2026-07-12 15:59 cache/indicators_GBPUSD_M15.json
2026-07-12 15:59 cache/indicators_GBPUSD_H4.json
2026-07-12 15:59 cache/indicators_GBPUSD_H1.json
2026-07-12 15:59 cache/indicators_GBPUSD_D1.json
2026-07-12 13:28 cache/indicators_EURUSD_M15.json
2026-07-12 13:28 cache/indicators_EURUSD_H4.json

