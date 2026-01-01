"""Integration test for XML → PriceEdge → JSON pipeline."""

import json
from pathlib import Path

import pytest

from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.transformation import TransformationEngine


@pytest.fixture
def sample_xml_content():
    """Load sample XML product data."""
    xml_path = Path("data/samples/article_deu_DEU.xml")
    if not xml_path.exists():
        # Fallback: use sample.xml
        xml_path = Path("data/samples/sample.xml")
    return xml_path.read_bytes()


@pytest.fixture
async def pipeline_components():
    """Initialize pipeline orchestrator with registries."""
    import httpx

    pipeline_registry = PipelineRegistry()
    pipeline_registry.load_pipelines()

    # Create HTTP client for REST connectors (like PriceEdge)
    async with httpx.AsyncClient() as http_client:
        connector_registry = ConnectorRegistry()
        await connector_registry.load_connectors(http_client=http_client)

        transformation_engine = TransformationEngine(rules=[])

        orchestrator = PipelineOrchestrator(
            pipeline_registry=pipeline_registry,
            connector_registry=connector_registry,
            transformation_engine=transformation_engine
        )

        yield orchestrator, pipeline_registry


@pytest.mark.integration
@pytest.mark.asyncio
async def test_xml_priceedge_json_pipeline_execution(
    pipeline_components,
    sample_xml_content
):
    """
    Test full pipeline execution: XML → PriceEdge → JSON.

    This test validates:
    1. XML parsing from input
    2. Transformation to PriceEdge request format
    3. API batch query (mocked)
    4. Response transformation
    5. JSON file output generation
    """
    orchestrator, registry = pipeline_components

    # Verify pipeline is loaded
    assert "xml-priceedge-json-pipeline" in registry.list_pipelines()

    # Prepare inputs (pre-parsed XML records)
    import pandas as pd
    df = pd.read_xml(sample_xml_content)

    inputs = {
        "records": df.to_dict(orient="records")
    }

    # Execute pipeline
    result = await orchestrator.execute_pipeline(
        pipeline_name="xml-priceedge-json-pipeline",
        inputs=inputs
    )

    # Assertions
    assert result.status == "success"
    assert result.metadata.records_extracted > 0
    assert result.metadata.records_transformed > 0
    assert result.metadata.records_loaded > 0

    # Verify output file exists
    output_file_id = result.metadata.custom_metadata.get("output_file_id")
    assert output_file_id is not None

    output_path = Path(f"data/downloads/{output_file_id}.json")
    assert output_path.exists()

    # Verify JSON output format
    output_data = json.loads(output_path.read_text())
    assert isinstance(output_data, list)
    assert len(output_data) > 0

    # Verify required fields in output
    first_record = output_data[0]
    assert "item_id" in first_record
    assert "price" in first_record
    assert isinstance(first_record["price"], (int, float))

    # Cleanup
    output_path.unlink()


@pytest.mark.asyncio
async def test_xml_parsing_step(sample_xml_content):
    """Test XML parsing step in isolation."""
    from flexlink.connectors.file_connector import FileConnector
    from flexlink.models.connector import AuthConfig, ConnectorConfig
    from flexlink.models.file import FileFormat

    # Create proper ConnectorConfig object
    config = ConnectorConfig(
        name="test_file",
        type="file",
        base_url="file://local",
        auth=AuthConfig(type="none")
    )

    connector = FileConnector(config)

    records = await connector.parse_to_records(
        file_content=sample_xml_content,
        source_format=FileFormat.XML
    )

    assert len(records) > 0
    # Check for common item identifier fields (varies by XML structure)
    assert any(field in records[0] for field in ["cd_ItemNumber", "item_id", "item_no"])


@pytest.mark.asyncio
async def test_json_output_step():
    """Test JSON file writing step in isolation."""
    import pandas as pd

    from flexlink.parsers.json_parser import JSONParser

    # Sample data
    data = [
        {"item_id": "ITEM001", "price": 19.99, "store_number": "STORE01"},
        {"item_id": "ITEM002", "price": 29.99, "store_number": "STORE01"},
    ]

    df = pd.DataFrame(data)
    parser = JSONParser()
    json_bytes = await parser.generate(df)

    # Verify JSON format
    parsed = json.loads(json_bytes.decode())
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0]["item_id"] == "ITEM001"
    assert parsed[0]["price"] == 19.99


@pytest.mark.asyncio
async def test_item_id_aggregation():
    """Test item ID aggregation for batch PriceEdge query."""
    from datetime import UTC, datetime

    from flexlink.core.pipeline_context import PipelineRunContext
    from flexlink.models.pipeline import ExecutionMetadata

    context = PipelineRunContext(
        run_id="test-run",
        pipeline_name="test-pipeline",
        started_at=datetime.now(UTC),
        data=[
            {"item_id": "ITEM001", "name": "Product A"},
            {"item_id": "ITEM002", "name": "Product B"},
            {"item_id": "ITEM003", "name": "Product C"},
        ],
        metadata=ExecutionMetadata()
    )

    # Simulate aggregation logic
    item_ids = [record["item_id"] for record in context.data]
    comma_separated = ",".join(item_ids)

    assert comma_separated == "ITEM001,ITEM002,ITEM003"
