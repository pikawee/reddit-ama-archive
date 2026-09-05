from pathlib import Path


def test_deploy_workflow():
    workflow_path = Path(".github/workflows/deploy.yml")
    assert workflow_path.exists(), ".github/workflows/deploy.yml missing"
    content = workflow_path.read_text(encoding="utf-8")
    assert "build-and-deploy:" in content
    assert "contents: write" in content
    assert "pages: write" in content
    assert "id-token: write" in content
