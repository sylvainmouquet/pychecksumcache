# PyChecksumCache

A lightweight Python library that uses MD5 checksums to track file changes and execute code only when files have been modified. PyChecksumCache maintains a persistent cache of file checksums, making it ideal for build systems, asset processors, incremental compilers, and any tools that need efficient change detection.

## How It Works

```mermaid
flowchart TD
    subgraph "Individual Processing"
        A[File to process] --> B{Calculate MD5}
        B --> C[Current checksum]
        D[(Checksum cache)] --> E{Compare with cached checksum}
        C --> E
        
        E -->|Different or not in cache| F[Execute code]
        E -->|Same| G[Skip processing]
        
        F --> H[Update cache with new checksum]
    end
    
    style A fill:#f9f9f9,stroke:#333,stroke-width:2px
    style D fill:#c9e6ff,stroke:#0066cc,stroke-width:2px
    style F fill:#d9f7be,stroke:#389e0d,stroke-width:2px
    style G fill:#ffccc7,stroke:#cf1322,stroke-width:2px
```

```mermaid
flowchart TD
    subgraph "Individual Processing"
        A1[Input Files] --> B1{Check\nChecksums}
        B1 -->|Changed| C1[Process\nEach Changed File]
        B1 -->|Unchanged| D1[Skip\nUnchanged Files]
        C1 --> E1[Multiple\nOutput Files]
    end
    
    subgraph "Aggregate Processing"
        A2[Input Files] --> B2{Any File\nChanged?}
        B2 -->|Yes| C2[Process All Files\nTogether]
        B2 -->|No| D2[Skip\nProcessing]
        C2 --> E2[Single\nOutput File]
    end
    
    style A1 fill:#f9f9f9,stroke:#333,stroke-width:2px
    style A2 fill:#f9f9f9,stroke:#333,stroke-width:2px
    
    style C1 fill:#d9f7be,stroke:#389e0d,stroke-width:2px
    style C2 fill:#d9f7be,stroke:#389e0d,stroke-width:2px
    
    style D1 fill:#ffccc7,stroke:#cf1322,stroke-width:2px
    style D2 fill:#ffccc7,stroke:#cf1322,stroke-width:2px
    
    style E1 fill:#b5f5ec,stroke:#13a8a8,stroke-width:2px
    style E2 fill:#ffd666,stroke:#d48806,stroke-width:2px
```
## Features

- Track changes to files using MD5 checksums
- Persistent cache storage in JSON format
```bash
{
  "tests/file1.txt": "ff1e0283123d14cf8bd52ac449770017",
  "tests/file2.txt": "b445bf8b5da4cf880dd14e98c18c1bfa"
}
```
- Execute functions only when file content has changed
- Aggregate multiple files into a single output file
- Batch transform multiple files with automatic output management
- Full async/await support
- Works with Python 3.10+
- No external dependencies

## Installation

```bash
pip install pychecksumcache
```

Or with uv:

```bash
uv pip install pychecksumcache
```

## Quick Start

### Basic Usage

```python
import pytest
from pychecksumcache import PyChecksumCache
import os

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
```