import json
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_REVISION = "c6079616813545bb0c0da1f649e04de6d89dc366"


def test_production_release_uses_the_immutable_shared_oidc_caller() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/deploy-production.yml").read_text()

    assert re.search(r"on:\s*\n\s*workflow_run:", workflow)
    assert re.search(r'workflows:\s*\["ci-deploy"\]', workflow)
    assert re.search(r"branches:\s*\[main\]", workflow)
    assert re.search(r"actions:\s*read", workflow)
    assert re.search(r"contents:\s*read", workflow)
    assert re.search(r"id-token:\s*write", workflow)
    assert (
        "uses: mahmoudelfeelig/HetznerReleaseGateway/"
        f".github/workflows/release.yml@{GATEWAY_REVISION}"
    ) in workflow
    assert "source_sha: ${{ github.event.workflow_run.head_sha }}" in workflow
    assert "ci_run_id: ${{ github.event.workflow_run.id }}" in workflow


def test_caller_and_docs_expose_no_direct_host_deployment_surface() -> None:
    workflow = (REPOSITORY_ROOT / ".github/workflows/deploy-production.yml").read_text()
    readme = (REPOSITORY_ROOT / "README.md").read_text()

    assert not re.search(r"\$\{\{\s*secrets\.", workflow, re.IGNORECASE)
    assert not re.search(
        r"\b(?:ssh|scp|rsync)\b|/opt/|HETZNER_(?:HOST|USER|PATH|SSH_KEY)",
        workflow,
        re.IGNORECASE,
    )
    assert not re.search(
        r"\b(?:ssh|scp|rsync)\b|/opt/|"
        r"HETZNER_(?:HOST|USER|PATH|SSH_KEY)|git\s+pull|/mnt/[a-z]/",
        readme,
        re.IGNORECASE,
    )
    assert not (REPOSITORY_ROOT / "deploy/Caddyfile.host.example").exists()


def test_release_manifest_identifies_only_the_reviewed_ocpp_build_contract() -> None:
    manifest = json.loads(
        (REPOSITORY_ROOT / ".github/hetzner-release.json").read_text()
    )

    assert manifest["version"] == 1
    assert manifest["id"] == "ocpp"
    assert manifest["source"] == {
        "repository": "mahmoudelfeelig/OCPP-Demo",
        "default_branch": "main",
        "required_workflows": ["ci-deploy"],
    }
    assert manifest["release"]["strategy"] == "source-build"
    assert [
        component["name"] for component in manifest["release"]["components"]
    ] == ["backend", "frontend", "simulator"]
