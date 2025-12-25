"""Mapping configuration loader from YAML files."""

import logging
from pathlib import Path
from typing import Any

import yaml

from flexlink.models.mapping import MappingConfig

logger = logging.getLogger(__name__)

# Global cache for loaded mappings
_mapping_cache: dict[str, MappingConfig] = {}


def load_mapping_config(
    mapping_name: str,
    config_dir: Path = Path("config"),
    use_cache: bool = True
) -> MappingConfig:
    """
    Load a mapping configuration from YAML file.

    Args:
        mapping_name: Name of the mapping (without .yaml extension)
        config_dir: Base configuration directory (default: config/)
        use_cache: Whether to use cached mappings (default: True)

    Returns:
        MappingConfig instance

    Raises:
        FileNotFoundError: If mapping file doesn't exist
        ValueError: If mapping configuration is invalid
    """
    # Check cache first
    if use_cache and mapping_name in _mapping_cache:
        logger.debug(f"Using cached mapping: {mapping_name}")
        return _mapping_cache[mapping_name]

    # Find mapping file
    mappings_dir = config_dir / "mappings"
    mapping_file = mappings_dir / f"{mapping_name}.yaml"

    if not mapping_file.exists():
        raise FileNotFoundError(
            f"Mapping configuration not found: {mapping_file}\n"
            f"Available mappings: {list_available_mappings(config_dir)}"
        )

    try:
        # Load YAML
        with open(mapping_file, encoding="utf-8") as f:
            raw_data: dict[str, Any] = yaml.safe_load(f)

        if not raw_data:
            raise ValueError(f"Empty mapping file: {mapping_file}")

        # Validate with Pydantic
        mapping_config = MappingConfig.model_validate(raw_data)

        # Ensure name matches filename
        if mapping_config.name != mapping_name:
            logger.warning(
                f"Mapping name '{mapping_config.name}' doesn't match filename '{mapping_name}'. "
                f"Using filename as canonical name."
            )
            mapping_config.name = mapping_name

        # Cache mapping
        _mapping_cache[mapping_name] = mapping_config

        logger.info(
            f"Loaded mapping config: {mapping_name} "
            f"({len(mapping_config.mappings)} rules, "
            f"validation={'enabled' if mapping_config.validation else 'disabled'})"
        )

        return mapping_config

    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML file {mapping_file}: {e}")
        raise ValueError(f"Invalid YAML in {mapping_file}: {e}") from e
    except Exception as e:
        logger.error(f"Failed to load mapping config from {mapping_file}: {e}")
        raise ValueError(f"Invalid mapping config in {mapping_file}: {e}") from e


def load_all_mapping_configs(config_dir: Path = Path("config")) -> dict[str, MappingConfig]:
    """
    Load all mapping configurations from config/mappings/ directory.

    Args:
        config_dir: Base configuration directory (default: config/)

    Returns:
        Dictionary mapping names to MappingConfig instances
    """
    mappings: dict[str, MappingConfig] = {}
    mappings_dir = config_dir / "mappings"

    if not mappings_dir.exists():
        logger.warning(f"Mappings directory not found: {mappings_dir}")
        return mappings

    yaml_files = list(mappings_dir.glob("*.yaml")) + list(mappings_dir.glob("*.yml"))

    if not yaml_files:
        logger.warning(f"No mapping configuration files found in {mappings_dir}")
        return mappings

    for mapping_file in yaml_files:
        mapping_name = mapping_file.stem  # Filename without extension
        try:
            mapping_config = load_mapping_config(mapping_name, config_dir, use_cache=False)
            mappings[mapping_name] = mapping_config
        except Exception as e:
            logger.error(f"Failed to load mapping {mapping_name}: {e}")
            # Continue loading other mappings

    logger.info(f"Loaded {len(mappings)} mapping configurations")
    return mappings


def list_available_mappings(config_dir: Path = Path("config")) -> list[str]:
    """
    List available mapping configuration names.

    Args:
        config_dir: Base configuration directory

    Returns:
        List of mapping names (without .yaml extension)
    """
    mappings_dir = config_dir / "mappings"

    if not mappings_dir.exists():
        return []

    yaml_files = list(mappings_dir.glob("*.yaml")) + list(mappings_dir.glob("*.yml"))
    return [f.stem for f in yaml_files]


def clear_mapping_cache() -> None:
    """Clear the mapping configuration cache."""
    global _mapping_cache
    _mapping_cache.clear()
    logger.debug("Cleared mapping configuration cache")
