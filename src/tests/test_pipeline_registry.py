"""Tests for pipeline registry."""

import pytest
from pathlib import Path
from pydantic import ValidationError

from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.models.pipeline import PipelineConfig


def test_registry_initialization():
    """Test registry can be initialized."""
    registry = PipelineRegistry()
    assert registry.config_dir == Path("config/pipelines")
    assert len(registry._pipelines) == 0


def test_registry_custom_directory():
    """Test registry with custom directory."""
    registry = PipelineRegistry(config_dir="test/pipelines")
    assert registry.config_dir == Path("test/pipelines")


def test_load_pipelines_creates_directory_if_missing(tmp_path):
    """Test registry creates config dir if it doesn't exist."""
    config_dir = tmp_path / "pipelines"
    registry = PipelineRegistry(config_dir=config_dir)

    registry.load_pipelines()

    assert config_dir.exists()


def test_load_valid_pipeline(tmp_path):
    """Test loading a valid pipeline configuration."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create test pipeline YAML
    pipeline_yaml = config_dir / "test-pipeline.yaml"
    pipeline_yaml.write_text("""
name: test-pipeline
description: Test pipeline
steps:
  - name: extract
    type: extract
    connector: test-source
    method: GET
    path: /data
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    assert "test-pipeline" in registry.list_pipelines()
    config = registry.get_pipeline("test-pipeline")
    assert config.name == "test-pipeline"
    assert len(config.steps) == 1
    assert config.steps[0].name == "extract"


def test_load_invalid_yaml_skips_file(tmp_path, caplog):
    """Test that invalid YAML files are skipped with error logged."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create invalid YAML
    bad_yaml = config_dir / "bad.yaml"
    bad_yaml.write_text("invalid: [yaml: content")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    # Should not crash, just log error
    assert "Failed to load pipeline" in caplog.text
    assert len(registry.list_pipelines()) == 0


def test_load_pipeline_missing_required_fields(tmp_path, caplog):
    """Test validation error for missing required fields."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create pipeline missing 'steps'
    pipeline_yaml = config_dir / "incomplete.yaml"
    pipeline_yaml.write_text("""
name: incomplete-pipeline
description: Missing steps
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    assert "Failed to load pipeline" in caplog.text
    assert len(registry.list_pipelines()) == 0


def test_duplicate_pipeline_names(tmp_path, caplog):
    """Test error handling for duplicate pipeline names."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create two pipelines with same name
    for i in range(2):
        pipeline_yaml = config_dir / f"pipeline{i}.yaml"
        pipeline_yaml.write_text("""
name: duplicate-name
description: Duplicate
steps:
  - name: step1
    type: extract
    connector: test
    method: GET
    path: /
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    # Second file should fail to load
    assert "Duplicate pipeline name" in caplog.text


def test_get_pipeline_not_found():
    """Test KeyError when pipeline doesn't exist."""
    registry = PipelineRegistry()

    with pytest.raises(KeyError, match="Pipeline 'nonexistent' not found"):
        registry.get_pipeline("nonexistent")


def test_list_pipelines_empty():
    """Test listing pipelines when none are loaded."""
    registry = PipelineRegistry()
    assert registry.list_pipelines() == []


def test_list_pipelines_sorted(tmp_path):
    """Test that pipeline list is sorted alphabetically."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create pipelines with names that aren't alphabetical
    for name in ["zebra", "alpha", "beta"]:
        pipeline_yaml = config_dir / f"{name}.yaml"
        pipeline_yaml.write_text(f"""
name: {name}
steps:
  - name: step1
    type: extract
    connector: test
    method: GET
    path: /
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    pipelines = registry.list_pipelines()
    assert pipelines == ["alpha", "beta", "zebra"]


def test_reload_pipelines(tmp_path):
    """Test reloading pipeline configurations."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create initial pipeline
    pipeline_yaml = config_dir / "test.yaml"
    pipeline_yaml.write_text("""
name: test-pipeline
steps:
  - name: step1
    type: extract
    connector: test
    method: GET
    path: /
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()
    assert len(registry.list_pipelines()) == 1

    # Add another pipeline
    pipeline_yaml2 = config_dir / "test2.yaml"
    pipeline_yaml2.write_text("""
name: test-pipeline-2
steps:
  - name: step1
    type: load
    connector: test
""")

    # Reload
    registry.reload()
    assert len(registry.list_pipelines()) == 2


def test_get_all_pipelines(tmp_path):
    """Test getting all pipelines as dict."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    pipeline_yaml = config_dir / "test.yaml"
    pipeline_yaml.write_text("""
name: test-pipeline
steps:
  - name: step1
    type: extract
    connector: test
    method: GET
    path: /
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    all_pipelines = registry.get_all_pipelines()
    assert isinstance(all_pipelines, dict)
    assert "test-pipeline" in all_pipelines
    assert isinstance(all_pipelines["test-pipeline"], PipelineConfig)


def test_get_all_pipelines_returns_copy(tmp_path):
    """Test that get_all_pipelines returns a copy, not reference."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    pipeline_yaml = config_dir / "test.yaml"
    pipeline_yaml.write_text("""
name: test-pipeline
steps:
  - name: step1
    type: extract
    connector: test
    method: GET
    path: /
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()

    all_pipelines = registry.get_all_pipelines()
    all_pipelines.clear()

    # Original should still have pipelines
    assert len(registry.list_pipelines()) == 1
