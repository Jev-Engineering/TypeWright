"""Packaging metadata regression tests. No build, network, or inference required."""
import json
import re
import tomllib
from fnmatch import fnmatch
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


GATEWAY_REQUIREMENTS = "examples/ai-gateway/requirements.txt"


def _declared_locations(pyproject):
    """Map each declared Python requirement to where it is declared (#50)."""
    project = pyproject["project"]
    locations = {}
    for requirement in project["dependencies"]:
        locations.setdefault(requirement, set()).add("base dependencies")
    for extra, requirements in project["optional-dependencies"].items():
        for requirement in requirements:
            locations.setdefault(requirement, set()).add(extra)
    gateway = (ROOT / GATEWAY_REQUIREMENTS).read_text(encoding="utf-8")
    for line in gateway.splitlines():
        if line.strip() and not line.strip().startswith("#"):
            locations.setdefault(line.strip(), set()).add(GATEWAY_REQUIREMENTS)
    return locations


def _table_rows(block):
    rows = {}
    for line in block.splitlines():
        match = re.fullmatch(r"\| `([^`]+)` \| (.+) \|", line.strip())
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def _documented_locations(cell):
    locations = set(re.findall(r"`([^`]+)`", cell))
    if "base dependencies" in cell:
        locations.add("base dependencies")
    return locations


def test_dependency_doc_lists_every_declared_exact_pin_and_range(pyproject):
    # Expectations come from pyproject.toml and the gateway requirements, not from the doc (#50).
    section = _dependency_section()
    exact_heading = section.index("Exact pins")
    range_heading = section.index("Bounded ranges")
    exact_rows = _table_rows(section[exact_heading:range_heading])
    range_rows = _table_rows(section[range_heading:])
    declared = _declared_locations(pyproject)
    for requirement, locations in declared.items():
        table, rows = ("exact pins", exact_rows) if "==" in requirement else ("ranges", range_rows)
        assert requirement in rows, f"{requirement} missing from the documented {table}"
        assert _documented_locations(rows[requirement]) == locations, (
            f"'Declared in' for {requirement} is stale; it is declared in {sorted(locations)}")
    assert set(exact_rows) | set(range_rows) == set(declared), "Doc lists a requirement that is not declared"


def test_dependency_doc_build_system_sentence_matches_pyproject(pyproject):
    section = _dependency_section()
    start = section.index("The build backend requirements")
    sentence = section[start:section.index("\n\n", start)]
    documented = set(re.findall(r"`([^`]+)`", sentence)) - {"[build-system]"}
    assert documented == set(pyproject["build-system"]["requires"])


def test_dependency_doc_covers_exact_npm_pins():
    package = json.loads((ROOT / "examples" / "ai-gateway" / "package.json").read_text(encoding="utf-8"))
    section = _dependency_section()
    for name, version in package["dependencies"].items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"npm {name} is not an exact pin; update #50 docs"
        assert f"`{name}`" in section and f"`{version}`" in section, f"npm pin {name}@{version} undocumented"


LOCK_NAMES = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lock",
              "bun.lockb", "poetry.lock", "uv.lock", "Pipfile.lock", "pdm.lock", "Cargo.lock",
              "Gemfile.lock", "composer.lock"}
LOCK_PATTERNS = ("*.lock", "*lock*.txt", "*lock*.toml", "requirements*.lock", "constraints*.txt",
                 "*freeze*.txt")
# Ignored or local-only directories (see .gitignore); untracked local files there must not matter.
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
             ".mypy_cache", ".tox", "htmlcov", "build", "dist", "runs", ".s1", ".claude"}


def _lock_like_files():
    found = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in relative.parts[:-1]):
            continue
        if path.is_file() and (path.name in LOCK_NAMES or any(fnmatch(path.name, p) for p in LOCK_PATTERNS)):
            found.append(relative.as_posix())
    return sorted(found)


def test_dependency_doc_names_every_lock_like_file_in_the_tree():
    # Every lock-like file in the source tree must be named, with its scope, in the #50 section.
    section = _dependency_section()
    found = _lock_like_files()
    assert "examples/ai-gateway/package-lock.json" in found, "lock scan is not reaching nested directories"
    undocumented = [path for path in found if f"`{path}`" not in section]
    assert not undocumented, f"Lock-like files not named in docs/INTEGRATIONS.md: {undocumented}"
    assert "has no current resolved lock" in " ".join(section.split())
