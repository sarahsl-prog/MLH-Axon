# Axon Tests

This directory contains unit and integration tests for the Axon bot detection system.

## Test Structure

- `test_features.py` - Unit tests for feature extraction and attack pattern detection
- `test_honeypot.py` - Unit tests for classification logic
- `test_integration.py` - Integration tests for complete workflows

## Running Tests

### Install Test Dependencies

```bash
pip install -r tests/requirements_test.txt
```

### Run All Tests

```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html -v

# Run specific test file
pytest tests/test_features.py -v

# Run specific test class
pytest tests/test_features.py::TestSQLInjectionDetection -v

# Run specific test
pytest tests/test_features.py::TestSQLInjectionDetection::test_union_select -v
```

### Test Coverage

Generate a coverage report:

```bash
pytest tests/ --cov=src --cov-report=term-missing
```

View HTML coverage report:

```bash
pytest tests/ --cov=src --cov-report=html
open htmlcov/index.html
```

## Test Categories

### Unit Tests

Tests individual functions and modules in isolation:
- Feature extraction functions
- Attack pattern detection
- Classification scoring logic
- User agent parsing

### Integration Tests

Tests complete workflows:
- Attack detection end-to-end
- Legitimate traffic classification
- Multiple feature detectors working together
- Edge cases and boundary conditions

## Writing New Tests

When adding new features, follow these guidelines:

1. **Create a test class** for each module or feature area
2. **Use descriptive test names** that explain what is being tested
3. **Test edge cases** including empty inputs, very long inputs, unicode, etc.
4. **Test both positive and negative cases** (attacks and legitimate traffic)
5. **Use helper methods** to reduce code duplication

### Example Test

```python
class TestNewFeature:
    """Test description"""

    def test_normal_case(self):
        """Test normal behavior"""
        result = my_function("normal input")
        assert result == expected_value

    def test_edge_case(self):
        """Test edge case"""
        result = my_function("")
        assert result == expected_edge_value
```

## Continuous Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r tests/requirements_test.txt
      - run: pytest tests/ -v
```

## Test Data

For testing with realistic data, see:
- Example attack patterns in `test_integration.py`
- Sample user agents in `test_features.py`

## Known Limitations

- Tests do not cover Cloudflare Workers-specific functionality (WebSockets, Durable Objects)
- D1 database interactions are not tested (would require mocking)
- Real HTTP request handling requires a running worker environment

For full system testing, deploy to a test Workers environment and use the traffic capture scripts.
