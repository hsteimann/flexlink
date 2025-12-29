"""Tests for mappings API endpoints - UI MVP Support."""

from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from flexlink.main import app


def test_list_mappings_success():
    """Test listing all mappings for UI dropdown/selection."""
    client = TestClient(app)

    # Mock the settings and file system
    with patch("flexlink.api.mappings.get_settings") as mock_settings:
        # Create mock Path objects
        mock_config_dir = Mock(spec=Path)
        mock_mappings_dir = Mock(spec=Path)

        # Create mock YAML files
        mock_file1 = Mock(spec=Path)
        mock_file1.stem = "user-mapping"
        mock_file1.relative_to.return_value = Path("mappings/user-mapping.yaml")

        mock_file2 = Mock(spec=Path)
        mock_file2.stem = "product-mapping"
        mock_file2.relative_to.return_value = Path("mappings/product-mapping.yaml")

        # Setup mock mappings directory
        mock_mappings_dir.exists.return_value = True
        mock_mappings_dir.glob.return_value = [mock_file1, mock_file2]

        # Setup config_dir to return mappings_dir when divided
        mock_config_dir.__truediv__ = Mock(return_value=mock_mappings_dir)

        # Configure settings mock
        mock_settings_instance = Mock()
        mock_settings_instance.config_dir = mock_config_dir
        mock_settings.return_value = mock_settings_instance

        response = client.get("/api/v1/mappings")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure for UI
        assert "mappings" in data
        assert "count" in data
        assert data["count"] == 2
        assert isinstance(data["mappings"], list)

        # Verify mappings are sorted by name
        mappings = {m["name"]: m for m in data["mappings"]}
        assert "user-mapping" in mappings
        assert "product-mapping" in mappings

        # Verify mapping metadata
        assert mappings["user-mapping"]["path"] == "mappings/user-mapping.yaml"


def test_list_mappings_empty_directory():
    """Test empty mappings directory for UI."""
    client = TestClient(app)

    with patch("flexlink.api.mappings.get_settings") as mock_settings:
        mock_config_dir = Mock(spec=Path)
        mock_mappings_dir = Mock(spec=Path)

        mock_mappings_dir.exists.return_value = False
        mock_config_dir.__truediv__ = Mock(return_value=mock_mappings_dir)

        mock_settings_instance = Mock()
        mock_settings_instance.config_dir = mock_config_dir
        mock_settings.return_value = mock_settings_instance

        response = client.get("/api/v1/mappings")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["mappings"] == []


def test_list_mappings_no_yaml_files():
    """Test directory with no YAML files for UI."""
    client = TestClient(app)

    with patch("flexlink.api.mappings.get_settings") as mock_settings:
        mock_config_dir = Mock(spec=Path)
        mock_mappings_dir = Mock(spec=Path)

        mock_mappings_dir.exists.return_value = True
        mock_mappings_dir.glob.return_value = []

        mock_config_dir.__truediv__ = Mock(return_value=mock_mappings_dir)

        mock_settings_instance = Mock()
        mock_settings_instance.config_dir = mock_config_dir
        mock_settings.return_value = mock_settings_instance

        response = client.get("/api/v1/mappings")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["mappings"] == []


def test_mappings_response_format():
    """Test mapping response format matches UI expectations."""
    client = TestClient(app)

    with patch("flexlink.api.mappings.get_settings") as mock_settings:
        mock_config_dir = Mock(spec=Path)
        mock_mappings_dir = Mock(spec=Path)

        mock_file = Mock(spec=Path)
        mock_file.stem = "test-mapping"
        mock_file.relative_to.return_value = Path("mappings/test-mapping.yaml")

        mock_mappings_dir.exists.return_value = True
        mock_mappings_dir.glob.return_value = [mock_file]

        mock_config_dir.__truediv__ = Mock(return_value=mock_mappings_dir)

        mock_settings_instance = Mock()
        mock_settings_instance.config_dir = mock_config_dir
        mock_settings.return_value = mock_settings_instance

        response = client.get("/api/v1/mappings")

        assert response.status_code == 200
        data = response.json()

        # Verify each mapping has required fields for UI
        mapping = data["mappings"][0]
        assert "name" in mapping
        assert "path" in mapping
        assert isinstance(mapping["name"], str)
        assert isinstance(mapping["path"], str)
        assert mapping["name"] == "test-mapping"


def test_mappings_sorted_by_name():
    """Test that mappings are returned sorted by name for UI."""
    client = TestClient(app)

    with patch("flexlink.api.mappings.get_settings") as mock_settings:
        mock_config_dir = Mock(spec=Path)
        mock_mappings_dir = Mock(spec=Path)

        # Create files in non-alphabetical order
        files = []
        for name in ["zebra-mapping", "alpha-mapping", "middle-mapping"]:
            mock_file = Mock(spec=Path)
            mock_file.stem = name
            mock_file.relative_to.return_value = Path(f"mappings/{name}.yaml")
            files.append(mock_file)

        mock_mappings_dir.exists.return_value = True
        mock_mappings_dir.glob.return_value = files

        mock_config_dir.__truediv__ = Mock(return_value=mock_mappings_dir)

        mock_settings_instance = Mock()
        mock_settings_instance.config_dir = mock_config_dir
        mock_settings.return_value = mock_settings_instance

        response = client.get("/api/v1/mappings")

        assert response.status_code == 200
        data = response.json()

        # Verify sorted order
        names = [m["name"] for m in data["mappings"]]
        assert names == ["alpha-mapping", "middle-mapping", "zebra-mapping"]
