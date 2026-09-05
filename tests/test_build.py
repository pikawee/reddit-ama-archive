import subprocess
from pathlib import Path


def test_build_generates_dist():
    res = subprocess.run(["python", "scripts/build.py"], capture_output=True, text=True, check=False)
    assert res.returncode == 0, f"build.py failed with: {res.stderr}\n{res.stdout}"
    dist = Path("dist")
    assert dist.exists(), "dist directory not created"
    assert (dist / "index.html").exists(), "dist/index.html missing"
    assert (dist / ".nojekyll").exists(), "dist/.nojekyll missing"
    assert (dist / "assets" / "data" / "threads.json").exists(), "dist/assets/data/threads.json missing"
    assert (dist / "assets" / "data" / "1w78hmo.json").exists(), "dist/assets/data/1w78hmo.json missing"
    assert (dist / "assets" / "data" / "1w78hmo.js").exists(), "dist/assets/data/1w78hmo.js missing"
