"""
Integration tests for the Medical ETL API.

All 6 modules have existing raw files on disk — tests use run-existing mode
(no file upload required). The server must be running before executing these tests.

Usage:
    # Terminal 1: start server
    .venv\\Scripts\\uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --workers 1

    # Terminal 2: run tests
    .venv\\Scripts\\python tests/test_api.py [module]  # e.g. python tests/test_api.py cam
    # Or run all modules (slow — may take 10+ minutes):
    .venv\\Scripts\\python tests/test_api.py
"""

import sys
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 10  # seconds between status polls
MAX_WAIT = 1800     # 30 minutes total timeout per module

# Expected runtimes (seconds) — used to set initial sleep before polling
MODULE_INITIAL_WAIT = {
    "cam": 30,
    "cim": 30,
    "hct": 60,
    "mca": 120,
    "ssc": 180,
    "xhi": 180,
}

ALL_MODULES = ["cam", "cim", "hct", "mca", "ssc", "xhi"]


def test_health():
    resp = httpx.get(f"{BASE_URL}/api/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    assert resp.json()["status"] == "ok"
    print("[PASS] /api/health")


def test_modules_endpoint():
    resp = httpx.get(f"{BASE_URL}/api/modules")
    assert resp.status_code == 200
    data = resp.json()
    for module in ALL_MODULES:
        assert module in data, f"Module {module} missing from /api/modules"
    print("[PASS] /api/modules")


def run_module(module: str, client: httpx.Client) -> bool:
    """Run a module via run-existing, poll until done, and download output."""
    print(f"\n[{module.upper()}] Submitting run-existing...")
    resp = client.post(f"{BASE_URL}/api/{module}/run-existing")
    assert resp.status_code == 200, f"Submit failed: {resp.status_code} {resp.text}"
    job = resp.json()
    job_id = job["job_id"]
    print(f"[{module.upper()}] Job ID: {job_id} (status={job['status']})")

    # Test: 409 on download before done
    dl_resp = client.get(f"{BASE_URL}/api/{module}/jobs/{job_id}/download")
    assert dl_resp.status_code == 409, f"Expected 409 before completion, got {dl_resp.status_code}"
    print(f"[{module.upper()}] 409 pre-completion check passed")

    # Wait for initial processing
    initial_wait = MODULE_INITIAL_WAIT.get(module, 60)
    print(f"[{module.upper()}] Waiting {initial_wait}s before polling...")
    time.sleep(initial_wait)

    # Poll until done or failed
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        status_resp = client.get(f"{BASE_URL}/api/{module}/jobs/{job_id}")
        assert status_resp.status_code == 200, f"Status check failed: {status_resp.text}"
        status = status_resp.json()
        current = status["status"]
        elapsed = status.get("finished_at", time.time()) - status.get("started_at", time.time())
        print(f"[{module.upper()}] status={current} elapsed={elapsed:.0f}s")

        if current == "done":
            break
        if current == "failed":
            print(f"[{module.upper()}] FAILED. Log:\n{status.get('log', '')[-2000:]}")
            return False
        time.sleep(POLL_INTERVAL)
    else:
        print(f"[{module.upper()}] TIMEOUT after {MAX_WAIT}s")
        return False

    # Download the output file
    output_path = status.get("output_file")
    print(f"[{module.upper()}] output_file={output_path}")

    dl_resp = client.get(f"{BASE_URL}/api/{module}/jobs/{job_id}/download", follow_redirects=True)
    assert dl_resp.status_code == 200, f"Download failed: {dl_resp.status_code} {dl_resp.text[:500]}"
    assert len(dl_resp.content) > 0, "Downloaded file is empty"

    content_type = dl_resp.headers.get("content-type", "")
    assert "spreadsheetml" in content_type or "octet-stream" in content_type, \
        f"Unexpected content-type: {content_type}"

    # Verify downloaded file matches the output on disk
    if output_path and Path(output_path).exists():
        disk_size = Path(output_path).stat().st_size
        assert abs(len(dl_resp.content) - disk_size) < 1024, \
            f"Download size mismatch: got {len(dl_resp.content)}, disk={disk_size}"

    print(f"[{module.upper()}] Download OK ({len(dl_resp.content):,} bytes)")

    # Test: unknown job → 404
    bad_resp = client.get(f"{BASE_URL}/api/{module}/jobs/nonexistent-id")
    assert bad_resp.status_code == 404
    print(f"[{module.upper()}] 404 for unknown job_id passed")

    print(f"[{module.upper()}] ALL TESTS PASSED")
    return True


def test_upload_cam(client: httpx.Client):
    """Test the /process (upload) endpoint with CAM's existing data_new.xlsx."""
    cam_file = Path("src/CAM/data_new.xlsx")
    if not cam_file.exists():
        print("[SKIP] CAM upload test — data_new.xlsx not found")
        return

    print("\n[CAM-UPLOAD] Testing process endpoint with file upload...")
    with cam_file.open("rb") as f:
        resp = client.post(
            f"{BASE_URL}/api/cam/process",
            files={"data_new": ("data_new.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
    assert resp.status_code == 200, f"CAM upload failed: {resp.status_code} {resp.text}"
    job = resp.json()
    job_id = job["job_id"]
    print(f"[CAM-UPLOAD] Job ID: {job_id}")

    # Wait and verify it completes
    time.sleep(30)
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        s = client.get(f"{BASE_URL}/api/cam/jobs/{job_id}").json()
        if s["status"] in ("done", "failed"):
            break
        time.sleep(POLL_INTERVAL)

    assert s["status"] == "done", f"CAM upload job failed:\n{s.get('log', '')[-1000:]}"
    print("[CAM-UPLOAD] PASSED")


def main():
    modules_to_test = sys.argv[1:] if len(sys.argv) > 1 else ALL_MODULES

    with httpx.Client(timeout=60.0) as client:
        # Basic endpoint tests (fast)
        test_health()
        test_modules_endpoint()

        # Module pipeline tests
        results = {}
        for module in modules_to_test:
            if module not in ALL_MODULES:
                print(f"Unknown module: {module}. Choose from {ALL_MODULES}")
                continue
            results[module] = run_module(module, client)

        # Upload test (CAM only — simplest single-file module)
        if "cam" in modules_to_test:
            test_upload_cam(client)

    print("\n=== RESULTS ===")
    for m, ok in results.items():
        print(f"  {m.upper()}: {'PASS' if ok else 'FAIL'}")

    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
