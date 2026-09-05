import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_production_gate_is_fail_closed() -> None:
    env = {"SL_ENVIRONMENT": "staging", "SL_REAL_EMAIL_ENABLED": "false"}
    proc = subprocess.run(
        [str(ROOT / "scripts" / "production-gate.sh")],
        cwd=ROOT,
        env={**__import__("os").environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "real outbound email" in proc.stdout


def test_production_gate_rejects_real_email() -> None:
    env = {"SL_ENVIRONMENT": "production", "SL_REAL_EMAIL_ENABLED": "true"}
    proc = subprocess.run(
        [str(ROOT / "scripts" / "production-gate.sh")],
        cwd=ROOT,
        env={**__import__("os").environ, **env},
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode != 0
