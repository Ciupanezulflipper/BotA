from pathlib import Path
import unittest
from ops import vps_release_gate

class ReleaseGateTests(unittest.TestCase):
    def test_repository_gate_passes_but_production_ready_remains_no(self):
        result=vps_release_gate.evaluate(Path(__file__).resolve().parents[1])
        self.assertEqual(result["REPOSITORY_RELEASE_GATE"],"PASS")
        self.assertEqual(result["PRODUCTION_READY"],"NO")
        self.assertEqual(result["NEXT_GATE"],"R5_VPS_NO_SIDE_EFFECT_SHADOW")
        self.assertEqual([result[f"R{i}"] for i in range(5)],["PASS"]*5)
    def test_machine_contract_has_required_closures(self):
        result=vps_release_gate.evaluate(Path(__file__).resolve().parents[1])
        self.assertEqual(result["VPS_SHELL_PYTHON_IS_RELEASE_VENV"],"YES")
        self.assertEqual(result["CANONICAL_TELEGRAM_TRANSPORT_COUNT"],1)
        self.assertEqual(result["WATCHER_DECISION_PERSISTENCE_NON_VACUOUS"],"YES")
