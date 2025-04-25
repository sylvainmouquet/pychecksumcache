import pytest
from loguru import logger
import logging
import os

from pychecksumcache import PyChecksumCache

# For console output
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add this handler to your logger
logger = logging.getLogger("pychecksumcache")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

input_files = ["tests/file1.txt", "tests/file2.txt"]
output_folder = "output"
output_extension = ".generated.txt"

@pytest.mark.asyncio
async def test_pychecksumcache_skipped():
    # Define a transformation function
    def transform_func(input_path, output_path):
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
            content = infile.read()
            # Apply some transformation
            transformed = content.upper()  # For example, convert to uppercase
            outfile.write(transformed)

    # Perform the transformation
    results = PyChecksumCache().transform(input_files, output_folder, output_extension, transform_func)

    # See which files were processed
    for output_file, was_transformed in results:
        assert not was_transformed, f"Skipped (unchanged): {output_file}"
    assert os.path.exists("checksum_cache.json") is True

@pytest.mark.asyncio
async def test_pychecksumcache_transformed():
    # Define a transformation function
    def transform_func(input_path, output_path):
        with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
            content = infile.read()
            # Apply some transformation
            transformed = content.upper()  # For example, convert to uppercase
            outfile.write(transformed)

    # Perform the transformation
    if os.path.exists(".cache/checksum_cache_transformed.json"):
        os.remove(".cache/checksum_cache_transformed.json")
    results = PyChecksumCache(".cache/checksum_cache_transformed.json").transform(input_files, output_folder, output_extension, transform_func)

    # See which files were processed
    for output_file, was_transformed in results:
        assert was_transformed, f"Transformed: {output_file}"

    assert os.path.exists(".cache/checksum_cache_transformed.json") is True