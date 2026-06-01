from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dexbtx_miner.verifier import build_local_proof


class VerifierTest(unittest.TestCase):
    def test_solver_flags_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            solver = Path(tmp) / "btx-gbt-solve"
            solver.write_text("#!/bin/sh\necho 'usage: --daemon --share-target --backend'\n")
            solver.chmod(0o755)

            proof = build_local_proof(
                solver_path=str(solver),
                backend="cpu",
                require_cuda=False,
            )

            self.assertTrue(proof.solver_exists)
            self.assertTrue(proof.solver_supports_daemon)
            self.assertTrue(proof.solver_supports_share_target)
            self.assertTrue(proof.zero_cpu_fallback_gate)

    def test_missing_solver_rejects(self) -> None:
        proof = build_local_proof(
            solver_path="/tmp/not-a-real-btx-gbt-solve",
            backend="cuda",
            require_cuda=True,
        )

        self.assertFalse(proof.zero_cpu_fallback_gate)
        self.assertTrue(proof.errors)


if __name__ == "__main__":
    unittest.main()
