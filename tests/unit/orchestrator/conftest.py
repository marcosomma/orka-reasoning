# Local conftest to override parent conftest fixtures for this directory
import pytest

# Override the auto-use fixtures from parent conftest
@pytest.fixture
def mock_external_services():
    """Disabled fixture for template_helpers tests."""
    pass
