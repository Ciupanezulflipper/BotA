# Historical Replay Audit Stop-Depth Policy

## Runtime investigation stop point

- [proven] The failure class is established: partial runtime configuration loss.
- [proven] The preserved July 8 snapshots establish exact missing-configuration observation points.
- [proven] Watcher and supervisor recovery evidence is established.
- [not proven] The original configuration-loss timestamp is known.
- [not proven] The entire long gap was continuously down.
- [proven] Those unresolved periods must remain `UNKNOWN`.

## Stop decision

- [inferred] Do not continue broad runtime keyword searches.
- [inferred] Do not attempt to convert the long gap into a continuous `DOWN` epoch without new primary evidence.
- [inferred] Continue only work that directly enables:
  - [inferred] canonical runtime classification;
  - [inferred] cycle operability;
  - [inferred] operational safeguards;
  - [inferred] data-integrity verification;
  - [inferred] production/replay parity.

## Reopen conditions

- [inferred] Reopen runtime forensics only when new primary evidence appears, such as:
  - [inferred] a preserved crontab snapshot before July 8;
  - [inferred] an Android or Termux service log proving process interruption;
  - [inferred] a timestamped updater execution ledger;
  - [inferred] a recovery command transcript with verified timestamps;
  - [inferred] immutable external monitoring evidence.

## Completion boundary

- [inferred] Runtime forensics is considered sufficiently deep when:
  - [inferred] weaknesses are registered;
  - [inferred] safeguards are prioritized;
  - [inferred] canonical runtime evidence validates;
  - [inferred] cycle classifications behave correctly;
  - [inferred] unresolved periods remain explicit.
