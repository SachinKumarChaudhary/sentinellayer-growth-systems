import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_gate(**overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(overrides)
    return subprocess.run(
        ["bash", str(ROOT / "scripts" / "production-gate.sh")],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_production_gate_is_fail_closed() -> None:
    proc = run_gate(
        SL_ENVIRONMENT="staging",
        SL_REAL_EMAIL_ENABLED="false",
    )
    assert proc.returncode == 0
    assert "email" in proc.stdout


def test_production_gate_rejects_real_email() -> None:
    proc = run_gate(
        SL_ENVIRONMENT="production",
        SL_REAL_EMAIL_ENABLED="true",
    )
    assert proc.returncode != 0
