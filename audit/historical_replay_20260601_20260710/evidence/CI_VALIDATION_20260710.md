# Historical Replay Sidecar — CI Validation Evidence

- [proven] Validation date: `2026-07-10` UTC.
- [proven] Validated branch head: `00116d9bb40cbcb9a63329edd115fb02c10ac587`.
- [proven] GitHub Actions workflow: `Historical replay sidecar`.
- [proven] Workflow run ID: `29130498160`.
- [proven] Workflow run number: `124`.
- [proven] Workflow conclusion: `success`.
- [proven] Job ID: `86484795284`.
- [proven] Job name: `synthetic-validation`.
- [proven] Production-import prohibition step: `success`.
- [proven] Synthetic test step: `success`.
- [proven] Machine-readable integrity proof step: `success`.
- [proven] Proof-status validation step: `success`.
- [proven] Evidence upload step: `success`.
- [proven] Pytest result: `97 passed`, `0 failures`, `0 errors`, `0 skipped`.
- [proven] JUnit execution time reported by pytest: `0.339` seconds.
- [proven] Retained artifact ID: `8241853852`.
- [proven] Retained artifact name: `historical-replay-synthetic-validation`.
- [proven] Retained artifact digest: `sha256:3c1de9cae58ad961489f8903aeebb96b69f593b478017e606aa9c7c966e5335e`.
- [proven] Artifact expiry timestamp: `2026-08-09T23:30:39Z`.
- [proven] Synthetic proof status: `PASS`.
- [proven] Synthetic proof artifact count: `4`.
- [proven] Synthetic proof artifact-index SHA-256: `a69e9c6ffcbc6cc2a55e164a5759f45d5bb1653a3d68c9b4e24b030bdccedee5`.
- [proven] Tamper detection: `PASS`; mutation was detected through an artifact-size mismatch.
- [proven] Independent repository Security Scan run `29130498177` also concluded `success` for the same validated head.

## Scope limitation

- [proven] This evidence validates the isolated synthetic sidecar tests and tamper-proof workflow only.
- [not proven] It does not validate live OANDA entitlement, complete historical coverage, Dukascopy live acquisition, production-equivalent replay results, or final forensic conclusions.
- [not proven] The BotA session is not closed; the required root state files and `handoff_pack.sh` verification remain outstanding.
