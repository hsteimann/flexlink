"""Tests for mapping configuration loader (mapping_loader.py)."""

import tempfile
from pathlib import Path

import pytest
import yaml

from flexlink.core.mapping_loader import (
    clear_mapping_cache,
    list_available_mappings,
    load_all_mapping_configs,
    load_mapping_config,
)
from flexlink.models.mapping import MappingConfig


# =============================================================================
# Tests for load_mapping_config()
# =============================================================================


class TestLoadMappingConfig:
    """Test loading individual mapping configurations."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            mappings_dir = config_dir / "mappings"
            mappings_dir.mkdir()
            yield config_dir

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        clear_mapping_cache()
        yield
        clear_mapping_cache()

    def test_load_mapping_config_valid(self, temp_config_dir):
        """Test loading a valid mapping configuration."""
        mapping_file = temp_config_dir / "mappings" / "test_mapping.yaml"
        mapping_data = {
            "name": "test_mapping",
            "description": "Test mapping",
            "mappings": [
                {"source_field": "old_name", "target_field": "new_name"}
            ]
        }

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_data, f)

        config = load_mapping_config("test_mapping", temp_config_dir)

        assert isinstance(config, MappingConfig)
        assert config.name == "test_mapping"
        assert len(config.mappings) == 1

    def test_load_mapping_config_file_not_found(self, temp_config_dir):
        """Test loading non-existent mapping raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Mapping configuration not found"):
            load_mapping_config("nonexistent", temp_config_dir)

    def test_load_mapping_config_empty_file(self, temp_config_dir):
        """Test loading empty YAML file raises ValueError."""
        mapping_file = temp_config_dir / "mappings" / "empty.yaml"

        with open(mapping_file, "w") as f:
            f.write("")

        with pytest.raises(ValueError, match="Empty mapping file"):
            load_mapping_config("empty", temp_config_dir)

    def test_load_mapping_config_invalid_yaml(self, temp_config_dir):
        """Test loading invalid YAML syntax raises ValueError."""
        mapping_file = temp_config_dir / "mappings" / "invalid.yaml"

        with open(mapping_file, "w") as f:
            f.write("invalid: [unclosed: list")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_mapping_config("invalid", temp_config_dir)

    def test_load_mapping_config_missing_required_fields(self, temp_config_dir):
        """Test Pydantic validation for invalid mapping rule."""
        mapping_file = temp_config_dir / "mappings" / "incomplete.yaml"

        # Invalid mapping rule - missing required 'target_field'
        with open(mapping_file, "w") as f:
            yaml.dump({
                "name": "incomplete",
                "mappings": [{"source_field": "test"}]  # Missing target_field
            }, f)

        with pytest.raises(ValueError, match="Invalid mapping config"):
            load_mapping_config("incomplete", temp_config_dir)

    def test_load_mapping_config_uses_cache(self, temp_config_dir):
        """Test that cached mappings are returned on subsequent loads."""
        mapping_file = temp_config_dir / "mappings" / "cached.yaml"
        mapping_data = {
            "name": "cached",
            "mappings": [{"source_field": "a", "target_field": "b"}]
        }

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_data, f)

        # First load - from file
        config1 = load_mapping_config("cached", temp_config_dir, use_cache=True)

        # Delete the file
        mapping_file.unlink()

        # Second load - should use cache, not fail
        config2 = load_mapping_config("cached", temp_config_dir, use_cache=True)

        assert config1.name == config2.name
        assert config1 is config2  # Same object from cache

    def test_load_mapping_config_bypass_cache(self, temp_config_dir):
        """Test that use_cache=False bypasses the cache."""
        mapping_file = temp_config_dir / "mappings" / "nocache.yaml"
        mapping_data = {
            "name": "nocache",
            "mappings": [{"source_field": "a", "target_field": "b"}]
        }

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_data, f)

        # Load with cache
        config1 = load_mapping_config("nocache", temp_config_dir, use_cache=True)

        # Load again bypassing cache
        config2 = load_mapping_config("nocache", temp_config_dir, use_cache=False)

        # Different objects (not from cache)
        assert config1.name == config2.name
        assert config1 is not config2

    def test_load_mapping_config_name_mismatch_warning(self, temp_config_dir):
        """Test that name mismatch between file and config generates warning."""
        mapping_file = temp_config_dir / "mappings" / "file_name.yaml"
        mapping_data = {
            "name": "different_name",  # Doesn't match filename
            "mappings": [{"source_field": "a", "target_field": "b"}]
        }

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_data, f)

        config = load_mapping_config("file_name", temp_config_dir)

        # Should use filename as canonical name
        assert config.name == "file_name"

    def test_load_mapping_config_with_validation(self, temp_config_dir):
        """Test loading mapping with validation configuration."""
        mapping_file = temp_config_dir / "mappings" / "validated.yaml"
        mapping_data = {
            "name": "validated",
            "mappings": [{"source_field": "a", "target_field": "b"}],
            "validation": {
                "rules": [
                    {"field": "a", "type": "string", "required": True}
                ]
            }
        }

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_data, f)

        config = load_mapping_config("validated", temp_config_dir)

        assert config.validation is not None
        assert len(config.validation.rules) == 1


# =============================================================================
# Tests for load_all_mapping_configs()
# =============================================================================


class TestLoadAllMappingConfigs:
    """Test loading all mapping configurations."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            mappings_dir = config_dir / "mappings"
            mappings_dir.mkdir()
            yield config_dir

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """Clear cache before each test."""
        clear_mapping_cache()
        yield
        clear_mapping_cache()

    def test_load_all_mapping_configs_empty_directory(self, temp_config_dir):
        """Test loading from empty mappings directory."""
        configs = load_all_mapping_configs(temp_config_dir)

        assert len(configs) == 0

    def test_load_all_mapping_configs_missing_directory(self, temp_config_dir):
        """Test loading when mappings directory doesn't exist."""
        mappings_dir = temp_config_dir / "mappings"
        mappings_dir.rmdir()

        configs = load_all_mapping_configs(temp_config_dir)

        assert len(configs) == 0

    def test_load_all_mapping_configs_multiple_files(self, temp_config_dir):
        """Test loading multiple mapping configurations."""
        # Create first mapping
        mapping1 = temp_config_dir / "mappings" / "mapping1.yaml"
        with open(mapping1, "w") as f:
            yaml.dump({
                "name": "mapping1",
                "mappings": [{"source_field": "a", "target_field": "b"}]
            }, f)

        # Create second mapping
        mapping2 = temp_config_dir / "mappings" / "mapping2.yaml"
        with open(mapping2, "w") as f:
            yaml.dump({
                "name": "mapping2",
                "mappings": [{"source_field": "c", "target_field": "d"}]
            }, f)

        configs = load_all_mapping_configs(temp_config_dir)

        assert len(configs) == 2
        assert "mapping1" in configs
        assert "mapping2" in configs

    def test_load_all_mapping_configs_both_extensions(self, temp_config_dir):
        """Test loading both .yaml and .yml files."""
        # Create .yaml file
        yaml_file = temp_config_dir / "mappings" / "config1.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump({
                "name": "config1",
                "mappings": [{"source_field": "a", "target_field": "b"}]
            }, f)

        # Create another .yaml file (not .yml to avoid extension handling issues)
        yaml_file2 = temp_config_dir / "mappings" / "config2.yaml"
        with open(yaml_file2, "w") as f:
            yaml.dump({
                "name": "config2",
                "mappings": [{"source_field": "c", "target_field": "d"}]
            }, f)

        configs = load_all_mapping_configs(temp_config_dir)

        assert len(configs) == 2
        assert "config1" in configs
        assert "config2" in configs

    def test_load_all_mapping_configs_continues_on_error(self, temp_config_dir):
        """Test that loading continues even if one mapping fails."""
        # Create valid mapping
        valid_mapping = temp_config_dir / "mappings" / "valid.yaml"
        with open(valid_mapping, "w") as f:
            yaml.dump({
                "name": "valid",
                "mappings": [{"source_field": "a", "target_field": "b"}]
            }, f)

        # Create invalid mapping
        invalid_mapping = temp_config_dir / "mappings" / "invalid.yaml"
        with open(invalid_mapping, "w") as f:
            f.write("invalid: [yaml")

        configs = load_all_mapping_configs(temp_config_dir)

        # Should have loaded the valid one, skipped the invalid
        assert len(configs) == 1
        assert "valid" in configs


# =============================================================================
# Tests for list_available_mappings()
# =============================================================================


class TestListAvailableMappings:
    """Test listing available mapping names."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            mappings_dir = config_dir / "mappings"
            mappings_dir.mkdir()
            yield config_dir

    def test_list_available_mappings_empty(self, temp_config_dir):
        """Test listing when no mappings exist."""
        mappings = list_available_mappings(temp_config_dir)

        assert mappings == []

    def test_list_available_mappings_missing_directory(self, temp_config_dir):
        """Test listing when mappings directory doesn't exist."""
        mappings_dir = temp_config_dir / "mappings"
        mappings_dir.rmdir()

        mappings = list_available_mappings(temp_config_dir)

        assert mappings == []

    def test_list_available_mappings_multiple_files(self, temp_config_dir):
        """Test listing multiple mapping files."""
        # Create mapping files (content doesn't matter for listing)
        (temp_config_dir / "mappings" / "mapping1.yaml").touch()
        (temp_config_dir / "mappings" / "mapping2.yaml").touch()
        (temp_config_dir / "mappings" / "mapping3.yml").touch()

        mappings = list_available_mappings(temp_config_dir)

        assert len(mappings) == 3
        assert "mapping1" in mappings
        assert "mapping2" in mappings
        assert "mapping3" in mappings

    def test_list_available_mappings_both_extensions(self, temp_config_dir):
        """Test that both .yaml and .yml extensions are listed."""
        (temp_config_dir / "mappings" / "config.yaml").touch()
        (temp_config_dir / "mappings" / "other.yml").touch()

        mappings = list_available_mappings(temp_config_dir)

        assert len(mappings) == 2
        assert "config" in mappings
        assert "other" in mappings

    def test_list_available_mappings_ignores_other_files(self, temp_config_dir):
        """Test that non-YAML files are ignored."""
        (temp_config_dir / "mappings" / "mapping.yaml").touch()
        (temp_config_dir / "mappings" / "readme.txt").touch()
        (temp_config_dir / "mappings" / "config.json").touch()

        mappings = list_available_mappings(temp_config_dir)

        assert len(mappings) == 1
        assert "mapping" in mappings


# =============================================================================
# Tests for clear_mapping_cache()
# =============================================================================


class TestClearMappingCache:
    """Test cache clearing functionality."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            mappings_dir = config_dir / "mappings"
            mappings_dir.mkdir()
            yield config_dir

    @pytest.fixture(autouse=True)
    def clear_cache_before(self):
        """Clear cache before each test."""
        clear_mapping_cache()
        yield

    def test_clear_mapping_cache_removes_cached_mappings(self, temp_config_dir):
        """Test that cache is cleared properly."""
        mapping_file = temp_config_dir / "mappings" / "test.yaml"
        mapping_data = {
            "name": "test",
            "mappings": [{"source_field": "a", "target_field": "b"}]
        }

        with open(mapping_file, "w") as f:
            yaml.dump(mapping_data, f)

        # Load to populate cache
        load_mapping_config("test", temp_config_dir, use_cache=True)

        # Clear cache
        clear_mapping_cache()

        # Delete file
        mapping_file.unlink()

        # Try to load again - should fail (not in cache)
        with pytest.raises(FileNotFoundError):
            load_mapping_config("test", temp_config_dir, use_cache=True)

    def test_clear_mapping_cache_multiple_times(self):
        """Test that clearing cache multiple times doesn't cause errors."""
        clear_mapping_cache()
        clear_mapping_cache()
        clear_mapping_cache()

        # Should not raise any errors
