import pytest
import logging
import os

from pychecksumcache import PyChecksumCache

# For console output
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

input_files = ["tests/file1.txt", "tests/file2.txt"]
output_folder = "tests/output"
output_extension = ".generated.txt"
aggregate_output_file = "tests/output/aggregated.txt"


@pytest.mark.asyncio
async def test_pychecksumcache_aggregate_skipped():
    # Define an aggregate transformation function
    def transform_func_aggregate(input_paths, output_path):
        with open(output_path, "w") as outfile:
            for input_path in input_paths:
                with open(input_path, "r") as infile:
                    content = infile.read()
                    # Transform each file
                    transformed = content.upper()
                    outfile.write(f"FILE: {os.path.basename(input_path)}\n")
                    outfile.write(transformed)
                    outfile.write("\n---\n")

    # Ensure the cache file exists from previous tests
    # This should cause the files to be skipped since they haven't changed
    results = PyChecksumCache().transform(
        input_files=input_files,
        aggregate_output_file=aggregate_output_file,
        transform_func_aggregate=transform_func_aggregate,
    )

    # There should be one result for the aggregate file
    assert len(results) == 1
    output_file, was_transformed = results[0]
    assert not was_transformed, f"Aggregate should have been skipped: {output_file}"


@pytest.mark.asyncio
async def test_pychecksumcache_aggregate_transformed():
    # Define an aggregate transformation function
    def transform_func_aggregate(input_paths, output_path):
        with open(output_path, "w") as outfile:
            for input_path in input_paths:
                with open(input_path, "r") as infile:
                    content = infile.read()
                    # Transform each file
                    transformed = content.upper()
                    outfile.write(f"FILE: {os.path.basename(input_path)}\n")
                    outfile.write(transformed)
                    outfile.write("\n---\n")

    # Create a new cache file to ensure transformation happens
    cache_file = ".cache/checksum_cache_aggregate.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)

    # Perform the transformation
    results = PyChecksumCache(cache_file).transform(
        input_files=input_files,
        aggregate_output_file=aggregate_output_file,
        transform_func_aggregate=transform_func_aggregate,
    )

    # There should be one result for the aggregate file
    assert len(results) == 1
    output_file, was_transformed = results[0]
    assert was_transformed, f"Aggregate should have been transformed: {output_file}"

    # Verify the aggregate file exists and contains the expected content
    assert os.path.exists(aggregate_output_file), (
        f"Aggregate file was not created: {aggregate_output_file}"
    )

    with open(aggregate_output_file, "r") as f:
        content = f.read()
        assert "FILE: file1.txt" in content, (
            "First file not included in aggregate output"
        )
        assert "FILE: file2.txt" in content, (
            "Second file not included in aggregate output"
        )
        assert "FILE 1" in content.upper(), (
            "Transformed content not found in aggregate output"
        )
        assert "FILE 2" in content.upper(), (
            "Transformed content not found in aggregate output"
        )


@pytest.mark.asyncio
async def test_pychecksumcache_default_aggregate_function():
    """Test that the default aggregate function works correctly."""

    # Create a new cache file to ensure transformation happens
    cache_file = ".cache/checksum_cache_default_aggregate.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)

    # Use the default aggregate function
    aggregate_file = "tests/output/default_aggregated.txt"
    results = PyChecksumCache(cache_file).transform(
        input_files=input_files, aggregate_output_file=aggregate_file
    )

    # There should be one result for the aggregate file
    assert len(results) == 1
    output_file, was_transformed = results[0]
    assert was_transformed, f"Aggregate should have been transformed: {output_file}"

    # Verify the aggregate file exists
    assert os.path.exists(aggregate_file), (
        f"Default aggregate file was not created: {aggregate_file}"
    )


@pytest.mark.asyncio
async def test_pychecksumcache_async_aggregate():
    """Test the async version of the aggregate transformation."""

    # Define an async aggregate transformation function
    async def transform_func_aggregate_async(input_paths, output_path):
        with open(output_path, "w") as outfile:
            for input_path in input_paths:
                with open(input_path, "r") as infile:
                    content = infile.read()
                    # Transform each file
                    transformed = content.upper()
                    outfile.write(f"ASYNC FILE: {os.path.basename(input_path)}\n")
                    outfile.write(transformed)
                    outfile.write("\n---\n")

    # Create a new cache file to ensure transformation happens
    cache_file = ".cache/checksum_cache_async_aggregate.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)

    # Perform the async transformation
    aggregate_file = "tests/output/async_aggregated.txt"
    cache = PyChecksumCache(cache_file)
    results = await cache.transform_async(
        input_files=input_files,
        aggregate_output_file=aggregate_file,
        transform_func_aggregate=transform_func_aggregate_async,
    )

    # There should be one result for the aggregate file
    assert len(results) == 1
    output_file, was_transformed = results[0]
    assert was_transformed, (
        f"Async aggregate should have been transformed: {output_file}"
    )

    # Verify the aggregate file exists and contains the expected content
    assert os.path.exists(aggregate_file), (
        f"Async aggregate file was not created: {aggregate_file}"
    )

    with open(aggregate_file, "r") as f:
        content = f.read()
        assert "ASYNC FILE: file1.txt" in content, (
            "First file not included in async aggregate output"
        )
        assert "ASYNC FILE: file2.txt" in content, (
            "Second file not included in async aggregate output"
        )
