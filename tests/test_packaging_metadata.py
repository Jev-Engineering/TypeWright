"""Packaging metadata regression tests. No build, network, or inference required."""
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_license_uses_spdx_string_not_deprecated_table(pyproject):
    # setuptools removes `project.license` as a TOML table after 2027-02-18.
    license_value = pyproject["project"]["license"]
    assert isinstance(license_value, str), "Use an SPDX string, not the deprecated {text = ...} table."
    assert license_value == "MIT"
    assert pyproject["project"]["license-files"] == ["LICENSE"]
    assert (ROOT / "LICENSE").is_file()


def test_build_backend_requires_setuptools_supporting_spdx(pyproject):
    # The SPDX string form of project.license needs setuptools>=77.
    requires = pyproject["build-system"]["requires"]
    assert "setuptools>=77" in requires


def test_runtime_dependencies_exclude_optimizer_and_sdk(pyproject):
    runtime = " ".join(pyproject["project"]["dependencies"]).lower()
    for package in ("dspy", "gepa", "typesafe-sdk"):
        assert package not in runtime, f"{package} must stay an optional extra, not a runtime dependency."


def test_optional_extras_pin_documented_integration_targets(pyproject):
    extras = pyproject["project"]["optional-dependencies"]
    assert "typesafe-sdk==0.7.0" in extras["live"]
    assert "dspy[litellm]>=3.3.1,<3.5" in extras["optimize"]
    assert "gepa==0.1.4" in extras["optimize"]


def test_checked_in_json_schemas_match_the_models():
    import json
    from pathlib import Path
    from typewright.hierarchy import HierarchyArtifact, HierarchySource
    from typewright.models import Program, UseCase

    directory = Path(__file__).resolve().parents[1] / "schemas"
    expected = {"usecase.schema.json": UseCase, "program.schema.json": Program,
                "hierarchy-source.schema.json": HierarchySource,
                "hierarchy-artifact.schema.json": HierarchyArtifact}
    assert {path.name for path in directory.glob("*.json")} == set(expected)
    for name, model in expected.items():
        stored = json.loads((directory / name).read_text(encoding="utf-8"))
        assert stored == model.model_json_schema(), f"{name} is stale; run `typewright schema --out schemas`"


def _dependency_section():
    text = (ROOT / "docs" / "INTEGRATIONS.md").read_text(encoding="utf-8")
    start = text.index("## Pinned and floating dependencies")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def _declared_requirements(pyproject):
    project = pyproject["project"]
    declared = list(project["dependencies"])
    for requirements in project["optional-dependencies"].values():
        declared.extend(requirements)
    gateway = (ROOT / "examples" / "ai-gateway" / "requirements.txt").read_text(encoding="utf-8")
    declared.extend(line.strip() for line in gateway.splitlines()
                    if line.strip() and not line.strip().startswith("#"))
    return set(declared)


def test_dependency_doc_lists_every_declared_exact_pin_and_range(pyproject):
    # Expectations come from pyproject.toml and the gateway requirements, not from the doc (#50).
    section = _dependency_section()
    exact_heading = section.index("Exact pins")
    range_heading = section.index("Bounded ranges")
    exact_block, range_block = section[exact_heading:range_heading], section[range_heading:]
    for requirement in _declared_requirements(pyproject):
        if "==" in requirement:
            assert f"`{requirement}`" in exact_block, f"{requirement} missing from documented exact pins"
        else:
            assert f"`{requirement}`" in range_block, f"{requirement} missing from documented ranges"


def test_dependency_doc_matches_absence_of_lock_file():
    lock_names = ("uv.lock", "poetry.lock", "Pipfile.lock", "pdm.lock", "pylock.toml",
                  "requirements.lock", "constraints.txt")
    assert not [name for name in lock_names if (ROOT / name).exists()], "Lock file present; update #50 docs."
    assert "no lock file" in _dependency_section().lower()
