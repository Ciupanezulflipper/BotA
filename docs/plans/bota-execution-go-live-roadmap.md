# BotA Execution & Go-Live Roadmap

- Last updated: 2026-11-28 (ChatGPT, execution evidence reconciliation)
- Purpose: single source of truth for where BotA is. Any AI session (Claude or ChatGPT) reads THIS file first instead of re-reading long continuity docs.
- Update rule: when a step changes status, update the Mermaid class, status table row and one changelog line in the same docs-only commit. Keep GitHub main and the Obsidian copy byte-identical; verify SHA-256 after each accepted update. Notify the founder whenever a step or chapter finishes. No production, merge or deploy changes without explicit founder approval.
- Detail: `docs/plans/2026-11-28-execution-layer-plan.md`

Legend: green = DONE, amber = IN PROGRESS / NEXT, grey = PENDING, red = GATE (must pass before continuing)

```mermaid
flowchart TD
    subgraph R["1. Production retirement"]
        R1["Legacy phone producer stopped<br/>+ launcher disabled"]
        R2["Supabase key rotated<br/>old key 401"]
        R3["Rollback file deleted"]
        R4["Telegram token rotation<br/>401/200 MATCH; admin test PASS"]
        R5["72h clean-producer window<br/>T0 24 Nov 20:00 UTC"]
        R6{{"GATE: real Hetzner signal<br/>opened + closed"}}
        R1 --> R2 --> R3 --> R4 --> R5 --> R6
    end

    subgraph P["2. Repairs = new generation"]
        P1["D1 fail-closed + 36h freshness<br/>exposure gate + deploy guard<br/>branch f11a3ae, 62/62 tests"]
        P2{{"GATE: 0 ACTIVE signals<br/>+ empty ProfitLab queue"}}
        P3["Merge + deploy<br/>(founder approval)"]
        P4["New generation clock starts<br/>episode 0"]
        P1 --> P2 --> P3 --> P4
    end

    subgraph B["3. Broker choice"]
        B1["Shortlist: IBKR vs cTrader EU broker"]
        B2["Verify eligibility, demo, small-lot pricing"]
        B3["Open demo on chosen broker"]
        B1 --> B2 --> B3
    end

    subgraph A["4. Phase A: demo executor (25-40 h)"]
        A1["Order per admitted signal<br/>SL/TP attached, idempotent ID"]
        A2["Reconciler + fill/spread/slippage log"]
        A3["Kill switch + tests + deploy"]
        A1 --> A2 --> A3
    end

    subgraph D["5. Phase B: demo evidence (4-8 weeks)"]
        D1["Collect >= 30 independent episodes"]
        D2["Weekly broker vs ledger comparison"]
        D1 --> D2
    end

    subgraph G["6. Go-live gates (all must pass)"]
        G1{{"Positive expectancy after costs<br/>beats random-entry baseline<br/>ledger matches broker<br/>drawdown within budget"}}
    end

    subgraph C["7. Phase C: small live (30-60 h)"]
        C1["Live adapter + sizing + daily loss limit"]
        C2["Auto-flatten + arm/disarm + secrets"]
        C3["Fund small account<br/>(money you can lose)"]
        C1 --> C2 --> C3
    end

    R6 --> P2
    P4 --> A1
    B3 --> A1
    A3 --> D1
    P4 --> D1
    D2 --> G1
    G1 --> C1

    classDef done fill:#2e7d32,stroke:#1b5e20,color:#ffffff;
    classDef active fill:#f9a825,stroke:#f57f17,color:#000000;
    classDef pending fill:#9e9e9e,stroke:#616161,color:#000000;
    classDef gate fill:#c62828,stroke:#8e0000,color:#ffffff;

    class R1,R2,R3,R4,P1 done;
    class R5 active;
    class R6,P2,G1 gate;
    class P3,P4,B1,B2,B3,A1,A2,A3,D1,D2,C1,C2,C3 pending;
```

## Status table

| # | Step | Status | Evidence / note |
|---|---|---|---|
| 1.1 | Legacy phone producer stopped + launcher disabled | DONE | 24 Nov; reboot persistence PASS |
| 1.2 | Supabase key rotated (bota_hetzner), old key revoked | DONE | 401 test 24 Nov 19:59:56 UTC |
| 1.3 | Supabase rollback file deleted | DONE | 25 Nov, guarded shred PASS |
| 1.4 | Telegram token rotation | DONE | Founder-reported execution 28 Nov: old getMe HTTP 401 at 14:09:00 UTC; new getMe HTTP 200 MATCH at 14:09:03 UTC. Replacement installed on Hetzner; ProfitLab Account / Admin Actions / Send Telegram Test: founder confirmed message received on 28 Nov (PASS; exact delivery timestamp not supplied). Consumers: Hetzner + phone (old fingerprint 7e18d1067664); scanner and send-telegram excluded. |
| 1.5 | 72h clean-producer window | IN PROGRESS | Earliest end 27 Nov 20:00 UTC has passed; extends until gate 1.6. Full clean-producer verification not re-audited in this session. |
| 1.6 | GATE: real Hetzner signal opened + closed | PENDING | Read-only Supabase signals query 28 Nov: 0 opened since T0 24 Nov 20:00 UTC, 0 opened and closed since T0; latest creation 23 Nov 16:30:04.819262 UTC, latest closure 23 Nov 19:15 UTC. Do not manufacture signals. |
| 2.1 | Repairs implemented (D1, exposure gate, deploy guard) | DONE | Branch fix/retirement-d1-active-signal-tests-20261125 @ f11a3ae; 62/62 tests independently verified |
| 2.2 | GATE: 0 ACTIVE + empty ProfitLab queue | PENDING | Checked at deploy time |
| 2.3 | Merge + deploy | PENDING | Founder approval required |
| 2.4 | New generation clock | PENDING | Later of 1.6 and 2.3 |
| 3.x | Broker choice (IBKR vs cTrader EU) | PENDING | Founder decision |
| 4.x | Phase A demo executor | PENDING | Starts after 2.4 and 3.x |
| 5.x | Phase B demo evidence | PENDING | >= 30 episodes |
| 6 | Go-live gates | PENDING | Pre-registered, all must pass |
| 7.x | Phase C small live | PENDING | Only after 6 |

## Changelog

- 2026-11-28: roadmap created (Claude).
- 2026-11-28: recorded Telegram getMe 401/200 MATCH evidence (admin test pending), verified no post-T0 signal lifecycle, retained R4/R5 active and R6 gate; added roadmap-first pointers to continuity files.
- 2026-11-28: step 1.4 DONE after founder confirmed receipt of the Telegram admin test; moved R4 to done; 1.5 and 1.6 unchanged.
