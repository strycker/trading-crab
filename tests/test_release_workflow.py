"""The release pipeline (CONTEXT D-13, DECISIONS G-24): tag-triggered, guarded, Trusted Publishing, no stored token.

Offline: these tests only read ``.github/workflows/publish-pypi.yml`` and ``RELEASING.md``. Nothing is published in 9.1.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]  # conftest points TC_ROOT_DIR at tmp_path, so not paths.root()
WORKFLOW = REPO / ".github" / "workflows" / "publish-pypi.yml"
PUBLISH_ACTION = "pypa/gh-action-pypi-publish@release/v1"


@pytest.fixture
def text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture
def wf(text: str) -> dict:
    return yaml.safe_load(text)


def _on(wf: dict) -> dict:
    return wf.get("on", wf.get(True))  # YAML 1.1 reads the bare key `on` as the boolean True


def _runs(job: dict) -> str:
    return "\n".join(step.get("run", "") for step in job["steps"])


def test_only_a_tag_push_or_a_manual_run_starts_a_release(wf):
    assert set(_on(wf)) == {"push", "workflow_dispatch"}  # no `release:`: a GitHub Release publishes nothing


def test_the_push_trigger_is_exactly_the_three_tag_prefixes(wf):
    assert _on(wf)["push"] == {"tags": ["v*", "lib-v*", "both-v*"]}  # no branch push ever publishes


def test_a_manual_run_chooses_package_and_target_and_defaults_to_testpypi(wf):
    inputs = _on(wf)["workflow_dispatch"]["inputs"]
    assert inputs["package"]["options"] == ["lib", "app", "both"]
    assert inputs["target"]["options"] == ["testpypi", "pypi"]
    assert inputs["target"]["default"] == "testpypi"


def test_only_the_publish_job_can_mint_an_upload_token(wf, text):
    assert wf["permissions"] == {"contents": "read"}
    minting = [name for name, job in wf["jobs"].items() if (job.get("permissions") or {}).get("id-token") == "write"]
    assert minting == ["publish"]
    assert wf["jobs"]["publish"]["permissions"] == {"id-token": "write"}
    assert text.count("id-token: write") == 1


def test_no_stored_secret_or_password_is_used(text):
    assert "secrets." not in text and "secrets[" not in text
    assert "password" not in text.lower() and "TWINE_" not in text


def test_the_publish_job_uploads_through_trusted_publishing_with_a_testpypi_rehearsal(wf):
    job = wf["jobs"]["publish"]
    assert job["needs"] == "build"  # a failed leg publishes nothing
    assert "pypi" in job["environment"] and "testpypi" in job["environment"]
    assert not [step for step in job["steps"] if "actions/checkout" in step.get("uses", "")]  # no repo code runs here
    uploads = [step for step in job["steps"] if step.get("uses") == PUBLISH_ACTION]
    assert len(uploads) == 2
    urls = [step["with"].get("repository-url") for step in uploads]
    assert urls.count("https://test.pypi.org/legacy/") == 1 and urls.count(None) == 1


def test_the_build_job_gates_each_leg_and_checks_version_metadata_and_wheels(wf):
    job = wf["jobs"]["build"]
    assert [leg["leg"] for leg in job["strategy"]["matrix"]["include"]] == ["lib", "app"]
    runs = _runs(job)
    for needle in ("PUBLISH:", "SKIP:", "twine check --strict", "scripts/check_wheels.sh dist-lib dist-app"):
        assert needle in runs, needle
    assert "bump both pyproject versions or retag" in runs
    assert "${{ inputs." not in runs and "${{ github.event.inputs." not in runs  # inputs reach scripts as env vars


def test_releasing_md_documents_the_setup_and_the_legacy_tag():
    releasing = (REPO / "RELEASING.md").read_text(encoding="utf-8")
    for needle in ("legacy/quarterly-final", "Trusted Publishing", "`pypi`", "`testpypi`", "PUBLISH:", "SKIP:"):
        assert needle in releasing, needle
