"""Pipeline registry for loading and managing pipeline configurations."""

import logging
from pathlib import Path

import yaml

from flexlink.models.pipeline import PipelineConfig

logger = logging.getLogger(__name__)


class PipelineRegistry:
    """
    Registry for pipeline configurations.

    Loads pipeline YAML files from config/pipelines/ directory
    and provides access to validated pipeline configs.
    """

    def __init__(self, config_dir: Path | str = "config/pipelines"):
        """
        Initialize pipeline registry.

        Args:
            config_dir: Directory containing pipeline YAML files
        """
        self.config_dir = Path(config_dir)
        self._pipelines: dict[str, PipelineConfig] = {}
        logger.info(f"Pipeline registry initialized (dir: {self.config_dir})")

    def load_pipelines(self) -> None:
        """
        Load all pipeline configurations from config directory.

        Creates directory if it doesn't exist.
        Continues loading on individual file errors.

        Raises:
            yaml.YAMLError: If YAML parsing fails critically
            ValidationError: If pipeline config is invalid
        """
        if not self.config_dir.exists():
            logger.warning(f"Pipeline config directory not found: {self.config_dir}")
            self.config_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created pipeline config directory: {self.config_dir}")
            return

        # Find all YAML files
        yaml_files = list(self.config_dir.glob("*.yaml")) + list(self.config_dir.glob("*.yml"))

        if not yaml_files:
            logger.warning(f"No pipeline YAML files found in {self.config_dir}")
            return

        # Load each file
        loaded_count = 0
        for yaml_file in yaml_files:
            try:
                self._load_pipeline_file(yaml_file)
                loaded_count += 1
            except Exception as e:
                logger.error(f"Failed to load pipeline from {yaml_file}: {e}")
                # Continue loading other files
                continue

        logger.info(f"Loaded {loaded_count}/{len(yaml_files)} pipelines successfully")

    def _load_pipeline_file(self, yaml_file: Path) -> None:
        """
        Load a single pipeline YAML file.

        Args:
            yaml_file: Path to YAML file

        Raises:
            ValueError: If duplicate pipeline name or invalid config
        """
        # Read and parse YAML
        with open(yaml_file, 'r') as f:
            raw_config = yaml.safe_load(f)

        # Validate with Pydantic
        pipeline_config = PipelineConfig.model_validate(raw_config)

        # Check for duplicate names
        if pipeline_config.name in self._pipelines:
            raise ValueError(
                f"Duplicate pipeline name '{pipeline_config.name}' "
                f"found in {yaml_file}"
            )

        # Store pipeline
        self._pipelines[pipeline_config.name] = pipeline_config

        logger.info(
            f"Loaded pipeline '{pipeline_config.name}' "
            f"({len(pipeline_config.steps)} steps) from {yaml_file.name}"
        )

    def get_pipeline(self, name: str) -> PipelineConfig:
        """
        Get pipeline configuration by name.

        Args:
            name: Pipeline name

        Returns:
            Pipeline configuration

        Raises:
            KeyError: If pipeline not found
        """
        if name not in self._pipelines:
            raise KeyError(f"Pipeline '{name}' not found")

        return self._pipelines[name]

    def list_pipelines(self) -> list[str]:
        """
        List all available pipeline names.

        Returns:
            List of pipeline names sorted alphabetically
        """
        return sorted(self._pipelines.keys())

    def reload(self) -> None:
        """
        Reload all pipeline configurations from disk.

        Clears current cache and re-loads all files.
        """
        logger.info("Reloading pipeline configurations")
        self._pipelines.clear()
        self.load_pipelines()

    def get_all_pipelines(self) -> dict[str, PipelineConfig]:
        """
        Get all loaded pipelines.

        Returns:
            Dictionary mapping pipeline name to config (copy)
        """
        return self._pipelines.copy()
