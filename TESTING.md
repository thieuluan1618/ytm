# Testing Guide for YTM CLI

This document provides comprehensive information about testing the YTM CLI project.

## Test Structure

The test suite is organized into several categories:

### Test Files

- `tests/test_utils.py` - Tests for utility functions (signal handling, terminal operations)
- `tests/test_config.py` - Tests for configuration management
- `tests/test_playlists.py` - Tests for playlist management functionality
- `tests/test_dislikes.py` - Tests for dislikes/filtering functionality
- `tests/test_auth.py` - Tests for authentication management
- `tests/test_lyrics_service.py` - Tests for lyrics service and parsing
- `tests/test_main.py` - Tests for CLI argument parsing and main entry points
- `tests/test_ui.py` - Tests for UI components and user interactions
- `tests/test_integration.py` - Integration tests for component interactions

### Test Categories

Tests are marked with pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (test component interactions)
- `@pytest.mark.slow` - Slow tests that may take longer to run
- `@pytest.mark.network` - Tests that require network access

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-cov pytest-mock
```

Or use the Makefile:

```bash
make install
```

### Quick Test Commands

```bash
# Run all tests with coverage
make test

# Run tests quickly (no coverage, faster for development)
make test-quick

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Generate and open coverage report
make test-coverage
```

### Manual pytest Commands

```bash
# Run all tests with coverage
pytest --cov=ytm_cli --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_playlists.py -v

# Run tests with specific marker
pytest -m unit -v

# Run tests without network tests
pytest -m "not network" -v

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Using the Test Runner

The project includes a custom test runner script:

```bash
# Run full test suite
python tests/test_runner.py full

# Run quick tests
python tests/test_runner.py quick

# Run specific test type
python tests/test_runner.py unit
python tests/test_runner.py integration

# Run specific test file
python tests/test_runner.py tests/test_playlists.py
```

## Test Configuration

### pytest.ini

The project uses `pytest.ini` for configuration:

- Test discovery patterns
- Coverage settings
- Marker definitions
- Default options

### Fixtures

Common test fixtures are defined in `tests/conftest.py`:

- `temp_dir` - Temporary directory for file operations
- `sample_song` - Sample song data for testing
- `sample_songs` - Multiple sample songs
- `sample_playlist_data` - Sample playlist structure
- `sample_dislikes_data` - Sample dislikes data
- `mock_ytmusic` - Mock YTMusic instance
- `mock_requests_session` - Mock requests session

## Writing Tests

### Test Structure

Follow this structure for new tests:

```python
"""Tests for ytm_cli.module_name module"""

import pytest
from unittest.mock import Mock, patch

from ytm_cli.module_name import ClassOrFunction


class TestClassName:
    """Tests for ClassName"""

    def test_method_success(self):
        """Test successful method execution"""
        # Arrange
        # Act
        # Assert

    def test_method_error_handling(self):
        """Test method error handling"""
        # Test error scenarios

    def test_method_edge_cases(self):
        """Test method edge cases"""
        # Test boundary conditions
```

### Best Practices

1. **Use descriptive test names** - Test names should clearly describe what is being tested
2. **Follow AAA pattern** - Arrange, Act, Assert
3. **Test both success and failure cases** - Include error handling tests
4. **Use appropriate fixtures** - Leverage existing fixtures for common test data
5. **Mock external dependencies** - Use mocks for file I/O, network calls, etc.
6. **Test edge cases** - Include boundary conditions and unusual inputs
7. **Keep tests isolated** - Each test should be independent

### Mocking Guidelines

- Mock external dependencies (file system, network, subprocess)
- Use `patch` for temporary mocking within test functions
- Use fixtures for reusable mocks
- Mock at the appropriate level (not too deep, not too shallow)

Example:

```python
def test_create_playlist_success(self, temp_dir):
    """Test successful playlist creation"""
    manager = PlaylistManager(temp_dir)
    
    with patch('builtins.print') as mock_print:
        result = manager.create_playlist("Test Playlist", "Description")
        
        assert result is True
        mock_print.assert_called_with("[green]✅ Created playlist: Test Playlist[/green]")
```

## Coverage Requirements

The project aims for **80% test coverage** minimum. Coverage reports show:

- Line coverage for each module
- Missing lines that need tests
- Overall project coverage

View coverage reports:

```bash
# Generate HTML coverage report
make test-coverage

# View terminal coverage report
pytest --cov=ytm_cli --cov-report=term-missing
```

## Continuous Integration

Tests should pass in CI environments. The test suite is designed to:

- Run without external dependencies
- Use temporary directories for file operations
- Mock network calls and external services
- Handle different operating systems

## Debugging Tests

### Running Individual Tests

```bash
# Run specific test method
pytest tests/test_playlists.py::TestPlaylistManager::test_create_playlist_success -v

# Run with pdb debugger
pytest tests/test_playlists.py::TestPlaylistManager::test_create_playlist_success --pdb

# Run with print statements visible
pytest tests/test_playlists.py -s
```

### Common Issues

1. **Import errors** - Check that modules are properly mocked
2. **File permission errors** - Ensure tests use temporary directories
3. **Mock assertion failures** - Verify mock calls match expected arguments
4. **Fixture scope issues** - Check fixture scope (function, class, module)

## Performance Testing

For performance-sensitive code, consider:

- Timing critical operations
- Testing with large datasets
- Memory usage monitoring
- Concurrent operation testing

## Test Data Management

- Use fixtures for reusable test data
- Keep test data minimal but representative
- Avoid hardcoded paths or system-specific data
- Use temporary files/directories for file operations

## Contributing Tests

When contributing new features:

1. Write tests for new functionality
2. Ensure existing tests still pass
3. Maintain or improve coverage percentage
4. Follow existing test patterns and conventions
5. Update this documentation if needed

## Troubleshooting

### Common Test Failures

1. **Module import errors** - Check Python path and module structure
2. **File not found errors** - Ensure tests use temporary directories
3. **Mock assertion errors** - Verify expected vs actual mock calls
4. **Timeout errors** - Check for infinite loops or blocking operations

### Getting Help

- Check test output for specific error messages
- Review similar tests for patterns
- Use pytest's verbose mode (`-v`) for detailed output
- Check fixture definitions in `conftest.py`
