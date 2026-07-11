# Q5 Inside-Evidence Audit

- [proven] Interval: `2026-06-22T17:45:00Z` to `2026-07-08T11:45:00Z`.
- [proven] Input evidence rows: `69`.

## Source counts

- [proven] `logs/cron.daily.log`: `69`

## Category counts

- [proven] `UNCLASSIFIED`: `69`

## EXPLICIT_FAILURE

- [proven] No matching rows.

## EXPLICIT_RECOVERY

- [proven] No matching rows.

## POSITIVE_RUNTIME

- [proven] No matching rows.

## UNRELATED_SUBSYSTEM

- [proven] No matching rows.

## UNCLASSIFIED

- [proven] `2026-06-22T18:10:53Z` `logs/cron.daily.log:1380` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-06-22T18:10:53Z server_hour=18 drift=-7251 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=3601;max_age_secs=28800;last_drift=-7251`
- [proven] `2026-06-22T19:10:51Z` `logs/cron.daily.log:1381` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-06-22T19:10:51Z server_hour=19 drift=-7250 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-05T12:11:56Z` `logs/cron.daily.log:1382` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T12:11:56Z server_hour=12 drift=-3716 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-05T13:11:51Z` `logs/cron.daily.log:1383` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T13:11:51Z server_hour=13 drift=-3711 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-05T14:11:53Z` `logs/cron.daily.log:1384` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T14:11:53Z server_hour=14 drift=-3713 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-05T15:11:57Z` `logs/cron.daily.log:1385` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T15:11:57Z server_hour=15 drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=3604;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T16:11:57Z` `logs/cron.daily.log:1386` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T16:11:57Z server_hour=16 drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=7204;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T17:12:02Z` `logs/cron.daily.log:1387` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T17:12:02Z server_hour=17 drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=10809;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T18:11:57Z` `logs/cron.daily.log:1388` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T18:11:57Z server_hour=18 drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=14404;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T19:12:12Z` `logs/cron.daily.log:1389` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T19:12:12Z server_hour=19 drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=18019;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T20:12:02Z` `logs/cron.daily.log:1390` — `GATE_SEND_START server_date=2026-07-05 server_utc=2026-07-05T20:12:02Z drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=21609;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T21:11:59Z` `logs/cron.daily.log:1419` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T21:11:59Z server_hour=21 drift=-3713 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=25206;max_age_secs=28800;last_drift=-3713`
- [proven] `2026-07-05T22:12:03Z` `logs/cron.daily.log:1420` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T22:12:03Z server_hour=22 drift=-3723 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-05T23:11:51Z` `logs/cron.daily.log:1421` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-05T23:11:51Z server_hour=23 drift=-3710 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T00:12:04Z` `logs/cron.daily.log:1422` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T00:12:04Z server_hour=0 drift=-3724 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T01:12:03Z` `logs/cron.daily.log:1423` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T01:12:03Z server_hour=1 drift=-3723 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T02:12:04Z` `logs/cron.daily.log:1424` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T02:12:04Z server_hour=2 drift=-3724 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T03:11:52Z` `logs/cron.daily.log:1425` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T03:11:52Z server_hour=3 drift=-3712 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T04:11:57Z` `logs/cron.daily.log:1426` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T04:11:57Z server_hour=4 drift=-3717 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T05:12:07Z` `logs/cron.daily.log:1427` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T05:12:07Z server_hour=5 drift=-3726 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T06:12:06Z` `logs/cron.daily.log:1428` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T06:12:06Z server_hour=6 drift=-3726 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=3599;max_age_secs=28800;last_drift=-3726`
- [proven] `2026-07-06T07:12:07Z` `logs/cron.daily.log:1429` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T07:12:07Z server_hour=7 drift=-3726 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=7200;max_age_secs=28800;last_drift=-3726`
- [proven] `2026-07-06T08:12:06Z` `logs/cron.daily.log:1430` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T08:12:06Z server_hour=8 drift=-3726 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=10799;max_age_secs=28800;last_drift=-3726`
- [proven] `2026-07-06T09:12:07Z` `logs/cron.daily.log:1431` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T09:12:07Z server_hour=9 drift=-3726 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=14400;max_age_secs=28800;last_drift=-3726`
- [proven] `2026-07-06T10:11:50Z` `logs/cron.daily.log:1432` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T10:11:50Z server_hour=10 drift=-3710 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T11:11:50Z` `logs/cron.daily.log:1433` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T11:11:50Z server_hour=11 drift=-3709 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T12:11:52Z` `logs/cron.daily.log:1434` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T12:11:52Z server_hour=12 drift=-3711 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T13:11:53Z` `logs/cron.daily.log:1435` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T13:11:53Z server_hour=13 drift=-3713 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T14:11:59Z` `logs/cron.daily.log:1436` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T14:11:59Z server_hour=14 drift=-3719 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T15:12:15Z` `logs/cron.daily.log:1437` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T15:12:15Z server_hour=15 drift=-3734 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T16:12:06Z` `logs/cron.daily.log:1438` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T16:12:06Z server_hour=16 drift=-3725 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T17:11:52Z` `logs/cron.daily.log:1439` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T17:11:52Z server_hour=17 drift=-3712 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T18:11:53Z` `logs/cron.daily.log:1440` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T18:11:53Z server_hour=18 drift=-3713 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T19:11:51Z` `logs/cron.daily.log:1441` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T19:11:51Z server_hour=19 drift=-3711 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T20:12:06Z` `logs/cron.daily.log:1442` — `GATE_SEND_START server_date=2026-07-06 server_utc=2026-07-06T20:12:06Z drift=-3725 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T21:12:01Z` `logs/cron.daily.log:1465` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T21:12:01Z server_hour=21 drift=-3721 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T22:11:58Z` `logs/cron.daily.log:1466` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T22:11:58Z server_hour=22 drift=-3718 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-06T23:11:54Z` `logs/cron.daily.log:1467` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-06T23:11:54Z server_hour=23 drift=-3714 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T00:11:53Z` `logs/cron.daily.log:1468` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T00:11:53Z server_hour=0 drift=-3713 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T01:11:50Z` `logs/cron.daily.log:1469` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T01:11:50Z server_hour=1 drift=-3710 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T02:11:50Z` `logs/cron.daily.log:1470` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T02:11:50Z server_hour=2 drift=-3709 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T03:11:53Z` `logs/cron.daily.log:1471` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T03:11:53Z server_hour=3 drift=-3712 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T04:11:53Z` `logs/cron.daily.log:1472` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T04:11:53Z server_hour=4 drift=-3712 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T05:12:04Z` `logs/cron.daily.log:1473` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T05:12:04Z server_hour=5 drift=-3724 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T06:12:05Z` `logs/cron.daily.log:1474` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T06:12:05Z server_hour=6 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=3601;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-07T07:12:04Z` `logs/cron.daily.log:1475` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T07:12:04Z server_hour=7 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=7200;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-07T08:12:05Z` `logs/cron.daily.log:1476` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T08:12:05Z server_hour=8 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=10801;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-07T09:12:04Z` `logs/cron.daily.log:1477` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T09:12:04Z server_hour=9 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=14400;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-07T10:12:05Z` `logs/cron.daily.log:1478` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T10:12:05Z server_hour=10 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=18001;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-07T11:11:57Z` `logs/cron.daily.log:1479` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T11:11:57Z server_hour=11 drift=-3717 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T12:11:57Z` `logs/cron.daily.log:1480` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T12:11:57Z server_hour=12 drift=-3717 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T13:12:02Z` `logs/cron.daily.log:1481` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T13:12:02Z server_hour=13 drift=-3722 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T14:11:48Z` `logs/cron.daily.log:1482` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T14:11:48Z server_hour=14 drift=-3708 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T15:12:07Z` `logs/cron.daily.log:1483` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T15:12:07Z server_hour=15 drift=-3726 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T16:11:56Z` `logs/cron.daily.log:1484` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T16:11:56Z server_hour=16 drift=-3716 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T17:12:07Z` `logs/cron.daily.log:1485` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T17:12:07Z server_hour=17 drift=-3727 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T18:11:50Z` `logs/cron.daily.log:1486` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T18:11:50Z server_hour=18 drift=-3710 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T19:11:54Z` `logs/cron.daily.log:1487` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T19:11:54Z server_hour=19 drift=-3714 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T20:11:52Z` `logs/cron.daily.log:1488` — `GATE_SEND_START server_date=2026-07-07 server_utc=2026-07-07T20:11:52Z drift=-3712 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T21:12:04Z` `logs/cron.daily.log:1511` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T21:12:04Z server_hour=21 drift=-3724 detail=target_hour=20;clock_source=live;status=DRIFT_WARN`
- [proven] `2026-07-07T22:12:15Z` `logs/cron.daily.log:1512` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T22:12:15Z server_hour=22 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=3611;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-07T23:12:04Z` `logs/cron.daily.log:1513` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-07T23:12:04Z server_hour=23 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=7200;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T00:12:05Z` `logs/cron.daily.log:1514` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T00:12:05Z server_hour=0 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=10801;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T01:12:04Z` `logs/cron.daily.log:1515` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T01:12:04Z server_hour=1 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=14400;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T02:12:04Z` `logs/cron.daily.log:1516` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T02:12:04Z server_hour=2 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=18000;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T03:12:04Z` `logs/cron.daily.log:1517` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T03:12:04Z server_hour=3 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=21600;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T04:12:04Z` `logs/cron.daily.log:1518` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T04:12:04Z server_hour=4 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=25200;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T05:12:04Z` `logs/cron.daily.log:1519` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T05:12:04Z server_hour=5 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=28800;max_age_secs=28800;last_drift=-3724`
- [proven] `2026-07-08T05:12:04Z` `logs/cron.daily.log:1520` — `GATE_SKIP status=OUTSIDE_WINDOW server_utc=2026-07-08T05:12:04Z server_hour=5 drift=-3724 detail=target_hour=20;clock_source=last_good;status=FALLBACK_LAST_GOOD;live_status=SERVER_CLOCK_UNAVAILABLE;age_secs=28800;max_age_secs=28800;last_drift=-3724`

## Evidentiary boundary

- [not proven] Keyword classification alone does not prove runtime state.
- [not proven] Positive evidence must be shown to represent the production watcher, not another subsystem.
- [not proven] Recovery evidence may establish an end boundary but not necessarily the complete start boundary.
- [not proven] Q5 remains UNKNOWN until each inside-interval row is reconciled.
