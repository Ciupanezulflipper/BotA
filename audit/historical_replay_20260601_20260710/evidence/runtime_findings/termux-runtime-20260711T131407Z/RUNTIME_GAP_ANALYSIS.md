# Runtime Gap Analysis

- [proven] Investigation window: `2026-06-01T00:00:00Z` to `2026-07-11T00:00:00Z`.
- [proven] Analysis uses only immutable captured copies of Termux evidence.
- [proven] Duplicate timestamps within each file were collapsed before gap calculation.
- [not proven] A single-source gap alone does not prove full BotA downtime.

## Source coverage

### supervisor

- [proven] Path: `logs/cron.supervisor.log`
- [proven] Present: `True`
- [proven] Unique timestamp count: `11657`
- [proven] First timestamp: `2026-06-01T00:00:00Z`
- [proven] Last timestamp: `2026-07-10T23:55:00Z`
- [proven] Large-gap threshold: `900` seconds
- [proven] Large gaps found: `9`

- [suspected] Gap `2026-06-01T03:35:02Z` to `2026-06-01T06:55:01Z` — `3.333` hours.
- [suspected] Gap `2026-06-02T02:15:02Z` to `2026-06-02T03:25:00Z` — `1.166` hours.
- [suspected] Gap `2026-06-03T14:25:02Z` to `2026-06-07T17:45:00Z` — `99.333` hours.
- [suspected] Gap `2026-06-08T08:40:02Z` to `2026-06-08T19:50:00Z` — `11.166` hours.
- [suspected] Gap `2026-06-12T20:20:01Z` to `2026-06-12T21:25:00Z` — `1.083` hours.
- [suspected] Gap `2026-06-13T21:10:01Z` to `2026-06-13T22:15:00Z` — `1.083` hours.
- [suspected] Gap `2026-06-17T20:30:01Z` to `2026-06-17T21:30:33Z` — `1.009` hours.
- [suspected] Gap `2026-06-18T12:05:00Z` to `2026-06-18T12:20:00Z` — `0.25` hours.
- [suspected] Gap `2026-06-22T17:40:01Z` to `2026-07-08T11:45:00Z` — `378.083` hours.

### heartbeat

- [proven] Path: `logs/cron.heartbeat.log`
- [proven] Present: `True`
- [proven] Unique timestamp count: `466`
- [proven] First timestamp: `2026-06-01T00:00:00Z`
- [proven] Last timestamp: `2026-07-10T23:00:00Z`
- [proven] Large-gap threshold: `7200` seconds
- [proven] Large gaps found: `6`

- [suspected] Gap `2026-06-01T03:00:00Z` to `2026-06-01T07:00:00Z` — `4.0` hours.
- [suspected] Gap `2026-06-03T14:00:00Z` to `2026-06-07T18:00:00Z` — `100.0` hours.
- [suspected] Gap `2026-06-08T08:00:01Z` to `2026-06-08T20:00:01Z` — `12.0` hours.
- [suspected] Gap `2026-06-12T20:00:00Z` to `2026-06-12T22:00:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-13T21:00:00Z` to `2026-06-13T23:00:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-22T17:00:00Z` to `2026-07-08T12:00:00Z` — `379.0` hours.

### signals

- [proven] Path: `logs/cron.signals.log`
- [proven] Present: `True`
- [proven] Unique timestamp count: `2068`
- [proven] First timestamp: `2026-06-01T07:15:10Z`
- [proven] Last timestamp: `2026-07-10T17:45:25Z`
- [proven] Large-gap threshold: `2700` seconds
- [proven] Large gaps found: `28`

- [suspected] Gap `2026-06-01T17:45:51Z` to `2026-06-02T06:30:07Z` — `12.738` hours.
- [suspected] Gap `2026-06-02T17:45:40Z` to `2026-06-03T05:00:35Z` — `11.249` hours.
- [suspected] Gap `2026-06-03T09:00:42Z` to `2026-06-03T13:45:03Z` — `4.739` hours.
- [suspected] Gap `2026-06-03T14:15:21Z` to `2026-06-08T07:45:06Z` — `113.496` hours.
- [suspected] Gap `2026-06-08T08:30:36Z` to `2026-06-09T03:00:18Z` — `18.495` hours.
- [suspected] Gap `2026-06-09T03:00:18Z` to `2026-06-09T07:15:09Z` — `4.247` hours.
- [suspected] Gap `2026-06-09T15:45:45Z` to `2026-06-10T06:45:05Z` — `14.989` hours.
- [suspected] Gap `2026-06-10T15:45:46Z` to `2026-06-11T07:00:08Z` — `15.239` hours.
- [suspected] Gap `2026-06-11T14:45:34Z` to `2026-06-12T02:00:06Z` — `11.242` hours.
- [suspected] Gap `2026-06-12T02:30:39Z` to `2026-06-12T06:15:05Z` — `3.741` hours.
- [suspected] Gap `2026-06-12T06:30:25Z` to `2026-06-12T09:00:05Z` — `2.494` hours.
- [suspected] Gap `2026-06-12T14:45:41Z` to `2026-06-15T05:00:05Z` — `62.24` hours.
- [suspected] Gap `2026-06-15T05:00:11Z` to `2026-06-15T06:15:03Z` — `1.248` hours.
- [suspected] Gap `2026-06-15T06:15:35Z` to `2026-06-15T07:15:11Z` — `0.993` hours.
- [suspected] Gap `2026-06-15T07:15:31Z` to `2026-06-15T10:30:08Z` — `3.244` hours.
- [suspected] Gap `2026-06-15T16:45:34Z` to `2026-06-16T04:45:09Z` — `11.993` hours.
- [suspected] Gap `2026-06-16T04:45:19Z` to `2026-06-16T07:30:05Z` — `2.746` hours.
- [suspected] Gap `2026-06-16T10:45:22Z` to `2026-06-16T16:15:05Z` — `5.495` hours.
- [suspected] Gap `2026-06-16T16:45:24Z` to `2026-06-17T05:45:04Z` — `12.994` hours.
- [suspected] Gap `2026-06-17T16:45:41Z` to `2026-06-18T07:00:06Z` — `14.24` hours.
- [suspected] Gap `2026-06-18T17:30:22Z` to `2026-06-19T06:45:07Z` — `13.246` hours.
- [suspected] Gap `2026-06-19T07:00:47Z` to `2026-06-19T11:00:07Z` — `3.989` hours.
- [suspected] Gap `2026-06-19T17:45:36Z` to `2026-06-22T10:15:06Z` — `64.492` hours.
- [suspected] Gap `2026-06-22T10:15:34Z` to `2026-06-22T12:15:19Z` — `1.996` hours.
- [suspected] Gap `2026-06-22T17:16:01Z` to `2026-07-08T11:45:07Z` — `378.485` hours.
- [suspected] Gap `2026-07-08T17:46:30Z` to `2026-07-09T05:00:03Z` — `11.226` hours.
- [suspected] Gap `2026-07-09T09:45:19Z` to `2026-07-09T14:30:09Z` — `4.747` hours.
- [suspected] Gap `2026-07-09T17:46:07Z` to `2026-07-10T10:00:10Z` — `16.234` hours.

### alerts

- [proven] Path: `logs/alerts.csv`
- [proven] Present: `True`
- [proven] Unique timestamp count: `300`
- [proven] First timestamp: `2026-06-01T08:45:22Z`
- [proven] Last timestamp: `2026-07-10T17:45:25Z`
- [proven] Large-gap threshold: `2700` seconds
- [proven] Large gaps found: `27`

- [suspected] Gap `2026-06-01T09:15:34Z` to `2026-06-01T10:01:19Z` — `0.762` hours.
- [suspected] Gap `2026-06-01T12:01:38Z` to `2026-06-01T13:16:05Z` — `1.241` hours.
- [suspected] Gap `2026-06-01T15:45:35Z` to `2026-06-02T12:30:39Z` — `20.751` hours.
- [suspected] Gap `2026-06-02T13:00:47Z` to `2026-06-02T15:15:50Z` — `2.251` hours.
- [suspected] Gap `2026-06-02T17:45:26Z` to `2026-06-03T05:01:15Z` — `11.264` hours.
- [suspected] Gap `2026-06-03T09:00:41Z` to `2026-06-03T13:45:21Z` — `4.744` hours.
- [suspected] Gap `2026-06-03T14:15:21Z` to `2026-06-08T07:45:28Z` — `113.502` hours.
- [suspected] Gap `2026-06-08T08:00:43Z` to `2026-06-09T12:00:32Z` — `27.997` hours.
- [suspected] Gap `2026-06-09T15:45:45Z` to `2026-06-10T06:45:27Z` — `14.995` hours.
- [suspected] Gap `2026-06-10T06:45:46Z` to `2026-06-10T08:01:14Z` — `1.258` hours.
- [suspected] Gap `2026-06-10T09:30:32Z` to `2026-06-10T12:30:32Z` — `3.0` hours.
- [suspected] Gap `2026-06-10T13:01:04Z` to `2026-06-11T08:45:46Z` — `19.745` hours.
- [suspected] Gap `2026-06-11T12:45:43Z` to `2026-06-15T06:15:20Z` — `89.494` hours.
- [suspected] Gap `2026-06-15T06:15:20Z` to `2026-06-15T07:15:30Z` — `1.003` hours.
- [suspected] Gap `2026-06-15T07:15:30Z` to `2026-06-15T10:30:27Z` — `3.249` hours.
- [suspected] Gap `2026-06-15T10:30:47Z` to `2026-06-15T15:30:15Z` — `4.991` hours.
- [suspected] Gap `2026-06-15T15:45:23Z` to `2026-06-16T10:30:37Z` — `18.754` hours.
- [suspected] Gap `2026-06-16T10:45:21Z` to `2026-06-16T16:15:14Z` — `5.498` hours.
- [suspected] Gap `2026-06-16T16:15:14Z` to `2026-06-17T05:45:24Z` — `13.503` hours.
- [suspected] Gap `2026-06-17T15:45:37Z` to `2026-06-18T10:30:28Z` — `18.747` hours.
- [suspected] Gap `2026-06-18T16:30:22Z` to `2026-06-22T10:15:33Z` — `89.753` hours.
- [suspected] Gap `2026-06-22T10:15:33Z` to `2026-06-22T12:15:50Z` — `2.005` hours.
- [suspected] Gap `2026-06-22T14:30:41Z` to `2026-06-22T15:16:37Z` — `0.766` hours.
- [suspected] Gap `2026-06-22T17:00:33Z` to `2026-07-08T11:45:26Z` — `378.748` hours.
- [suspected] Gap `2026-07-08T15:00:18Z` to `2026-07-09T06:15:29Z` — `15.253` hours.
- [suspected] Gap `2026-07-09T08:30:59Z` to `2026-07-09T09:30:17Z` — `0.988` hours.
- [suspected] Gap `2026-07-09T09:45:19Z` to `2026-07-10T16:45:19Z` — `31.0` hours.

### shadow_heartbeat

- [proven] Path: `logs/shadow_manager_heartbeat.txt`
- [proven] Present: `True`
- [proven] Unique timestamp count: `1866`
- [proven] First timestamp: `2026-06-01T00:00:24.246961Z`
- [proven] Last timestamp: `2026-07-10T23:45:04.923623Z`
- [proven] Large-gap threshold: `2700` seconds
- [proven] Large gaps found: `8`

- [suspected] Gap `2026-06-01T03:30:43.801002Z` to `2026-06-01T07:00:03.382307Z` — `3.489` hours.
- [suspected] Gap `2026-06-02T02:15:11.162455Z` to `2026-06-02T03:30:07.290007Z` — `1.249` hours.
- [suspected] Gap `2026-06-03T14:15:03.814241Z` to `2026-06-07T17:45:08.916253Z` — `99.501` hours.
- [suspected] Gap `2026-06-08T08:30:08.615509Z` to `2026-06-08T20:00:10.981342Z` — `11.501` hours.
- [suspected] Gap `2026-06-12T20:15:04.710809Z` to `2026-06-12T21:30:08.457387Z` — `1.251` hours.
- [suspected] Gap `2026-06-13T21:00:06.561236Z` to `2026-06-13T22:15:05.467072Z` — `1.249` hours.
- [suspected] Gap `2026-06-17T20:30:04.234095Z` to `2026-06-17T21:30:44.860060Z` — `1.011` hours.
- [suspected] Gap `2026-06-22T17:15:13.506268Z` to `2026-07-08T11:45:03.800829Z` — `378.497` hours.

### autostatus

- [proven] Path: `logs/cron.autostatus.log`
- [proven] Present: `True`
- [proven] Unique timestamp count: `464`
- [proven] First timestamp: `2026-06-01T00:04:00Z`
- [proven] Last timestamp: `2026-07-10T23:04:00Z`
- [proven] Large-gap threshold: `7200` seconds
- [proven] Large gaps found: `9`

- [suspected] Gap `2026-06-01T03:04:01Z` to `2026-06-01T07:04:01Z` — `4.0` hours.
- [suspected] Gap `2026-06-02T02:04:00Z` to `2026-06-02T04:04:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-03T14:04:00Z` to `2026-06-07T18:04:00Z` — `100.0` hours.
- [suspected] Gap `2026-06-08T08:04:00Z` to `2026-06-08T20:04:00Z` — `12.0` hours.
- [suspected] Gap `2026-06-12T20:04:00Z` to `2026-06-12T22:04:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-13T21:04:00Z` to `2026-06-13T23:04:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-17T20:04:00Z` to `2026-06-17T22:04:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-18T02:04:00Z` to `2026-06-18T04:04:00Z` — `2.0` hours.
- [suspected] Gap `2026-06-22T17:04:00Z` to `2026-07-08T12:04:01Z` — `379.0` hours.

## Cross-source quiet intervals

- [suspected] All selected sources silent from `2026-06-01T03:45:00Z` to `2026-06-01T06:45:00Z` — `3.0` hours.
- [suspected] All selected sources silent from `2026-06-03T14:30:00Z` to `2026-06-07T17:45:00Z` — `99.25` hours.
- [suspected] All selected sources silent from `2026-06-08T08:45:00Z` to `2026-06-08T19:45:00Z` — `11.0` hours.
- [suspected] All selected sources silent from `2026-06-13T21:15:00Z` to `2026-06-13T22:15:00Z` — `1.0` hours.
- [suspected] All selected sources silent from `2026-06-22T17:45:00Z` to `2026-07-08T11:45:00Z` — `378.0` hours.

## Interpretation boundary

- [not proven] A quiet interval is not automatically a watcher outage.
- [not proven] An active supervisor does not automatically prove successful signal evaluation.
- [not proven] Runtime DOWN requires corroboration from multiple independent artifacts or an explicit failure/recovery record.
- [not proven] Runtime UP requires evidence sufficiently close to each classified cycle.
