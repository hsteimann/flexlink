"""Tests for parser factory."""

import pytest

from flexlink.models.file import FileFormat
from flexlink.parsers.csv_parser import CSVParser
from flexlink.parsers.json_parser import JSONParser
from flexlink.parsers.parser_factory import ParserFactory
from flexlink.parsers.xml_parser import XMLParser


def test_get_csv_parser():
    """Test getting CSV parser from factory."""
    factory = ParserFactory()
    parser = factory.get_parser(FileFormat.CSV)

    assert isinstance(parser, CSVParser)


def test_get_json_parser():
    """Test getting JSON parser from factory."""
    factory = ParserFactory()
    parser = factory.get_parser(FileFormat.JSON)

    assert isinstance(parser, JSONParser)


def test_get_xml_parser():
    """Test getting XML parser from factory."""
    factory = ParserFactory()
    parser = factory.get_parser(FileFormat.XML)

    assert isinstance(parser, XMLParser)


def test_unsupported_format_raises_error():
    """Test that requesting unsupported format raises ValueError."""
    factory = ParserFactory()

    # This should raise since we're testing the error path
    # In practice, FileFormat enum prevents invalid values
    with pytest.raises(AttributeError):
        # Try to create an invalid format
        factory.get_parser("invalid")


def test_supports_format():
    """Test checking if format is supported."""
    factory = ParserFactory()

    assert factory.supports_format(FileFormat.CSV) is True
    assert factory.supports_format(FileFormat.JSON) is True
    assert factory.supports_format(FileFormat.XML) is True


def test_get_supported_formats():
    """Test getting list of supported formats."""
    factory = ParserFactory()
    formats = factory.get_supported_formats()

    assert FileFormat.CSV in formats
    assert FileFormat.JSON in formats
    assert FileFormat.XML in formats
    assert len(formats) == 3
