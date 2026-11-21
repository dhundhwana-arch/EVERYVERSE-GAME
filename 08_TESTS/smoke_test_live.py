"""
Live Deployment Smoke-Test Script for LIFEVERSE 2070 (Render + Neon PostgreSQL)
Usage: python3 08_TESTS/smoke_test_live.py https://your-render-url.onrender.com
"""
import sys
import httpx


def run_smoke_test(base_url: str) -> None:
    base = base_url.rstrip("/")
    print(f"Running LIFEVERSE 2070 live smoke tests against: {base}")

    r = httpx.get(f"{base}/health", timeout=20.0)
    r.raise_for_status()
    data = r.json()
    assert data["status"] == "ok", f"Unexpected health: {data}"
    assert data["branding"] == "CREATED BY DIVYESH BAMBHANIYA"
    assert r.headers.get("x-content-type-options") == "nosniff"
    print("[PASS] /health + Security Headers + Branding")

    reg = httpx.get(f"{base}/api/v1/careers/registry", timeout=20.0)
    reg.raise_for_status()
    assert reg.json()["count"] == 30
    print("[PASS] /api/v1/careers/registry (30 careers live)")

    npcs = httpx.get(f"{base}/api/v1/npcs/directory", timeout=20.0)
    npcs.raise_for_status()
    assert len(npcs.json()["npcs"]) >= 3
    print("[PASS] /api/v1/npcs/directory")

    lb = httpx.get(f"{base}/api/v1/life/leaderboards", timeout=20.0)
    lb.raise_for_status()
    assert "public_trust_leaders" in lb.json()
    print("[PASS] /api/v1/life/leaderboards")

    print("ALL LIVE SMOKE TESTS PASSED!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 08_TESTS/smoke_test_live.py <BASE_URL>")
        sys.exit(1)
    run_smoke_test(sys.argv[1])
