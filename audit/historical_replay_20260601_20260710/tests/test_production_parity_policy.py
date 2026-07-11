from pathlib import Path


def test_production_parity_policy_is_present_and_binding():
    root = Path(__file__).resolve().parents[1]
    policy = (root / "PRODUCTION_PARITY_POLICY.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")

    required_policy_phrases = (
        "not a second BotA",
        "not complete merely because it works inside the sidecar",
        "mapped to the corresponding production BotA file",
        "Silent adaptation",
        "Merge readiness requires demonstrated production parity",
    )
    for phrase in required_policy_phrases:
        assert phrase in policy

    assert "PRODUCTION_PARITY_POLICY.md" in readme
    assert "not a second BotA" in readme
    assert "silent adaptation is prohibited" in readme
