"""Test to verify pytest test reporter is working correctly"""

import pytest
from pathlib import Path


def test_reporter_basic():
    """Basic test to verify reporter captures results"""
    assert 1 + 1 == 2
    

def test_reporter_with_output():
    """Test with some output to capture"""
    result = "Hello from test reporter"
    print(f"Test output: {result}")
    assert result == "Hello from test reporter"


def test_reporter_failure_example():
    """Test that intentionally fails to verify failure reporting"""
    # This should be captured in the report
    expected = 5
    actual = 2 + 2
    assert actual == expected, f"Expected {expected} but got {actual}"


@pytest.mark.slow
def test_reporter_with_marker():
    """Test with custom marker"""
    import time
    time.sleep(0.1)  # Simulate slow test
    assert True


class TestReporterClass:
    """Test class to verify class-based test reporting"""
    
    def test_class_method(self):
        """Test method in a class"""
        data = {"key": "value"}
        assert data["key"] == "value"
    
    def test_class_method_with_fixture(self, tmp_path):
        """Test using pytest fixture"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()
        assert test_file.read_text() == "test content"