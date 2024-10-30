from datetime import datetime

import pytest

from cue.utils.id_generator import generate_id, generate_run_id


@pytest.mark.unit
def test_run_id_generator():
    """Test suite for run ID generator"""
    # Test 1: With timestamp (default behavior)
    run_id_with_timestamp = generate_run_id()
    print(f"\nTest 1 - With timestamp: {run_id_with_timestamp}")

    parts = run_id_with_timestamp.split("-")
    assert len(parts) == 2, "Run ID with timestamp should have exactly one hyphen"

    timestamp = parts[0]
    unique_id = parts[1]

    assert len(timestamp) == 14, "Timestamp should be 14 characters (YYYYMMDDHHMMSS)"
    assert len(unique_id) == 6, "Unique ID part should be 6 characters"

    # Validate timestamp format
    try:
        datetime.strptime(timestamp, "%Y%m%d%H%M%S")
        print("✓ Timestamp format is valid")
    except ValueError:
        raise AssertionError("Invalid timestamp format")

    # Test 2: Without timestamp
    run_id_no_timestamp = generate_run_id(include_timestamp=False)
    print(f"\nTest 2 - Without timestamp: {run_id_no_timestamp}")

    assert "-" not in run_id_no_timestamp, "Run ID without timestamp should not contain hyphen"
    assert len(run_id_no_timestamp) == 6, "Run ID without timestamp should be 6 characters"

    # Test 3: Uniqueness test
    print("\nTest 3 - Uniqueness test:")
    ids = set()
    num_tests = 1000

    for _ in range(num_tests):
        id1 = generate_run_id(include_timestamp=False)
        ids.add(id1)

    assert len(ids) == num_tests, f"Generated {len(ids)} unique IDs out of {num_tests} attempts"
    print(f"✓ Generated {num_tests} unique IDs successfully")

    # Test 4: Basic generate_id function
    custom_id = generate_id(prefix="test_", length=10)
    print(f"\nTest 4 - Custom ID with prefix: {custom_id}")
    assert custom_id.startswith("test_"), "Custom ID should start with given prefix"
    assert len(custom_id) == 15, "Custom ID length should be prefix length + specified length"

    print("\n✓ All tests passed successfully!")
