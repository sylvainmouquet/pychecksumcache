import hashlib
import os
import json
import shutil
import asyncio
from pathlib import Path
from typing import Callable, Dict, List, Union, Optional, Tuple, Any
from loguru import logger


class PyChecksumCache:
    """
    A utility class that uses MD5 checksums to track file changes and execute code only when files have been modified.
    Supports both synchronous and asynchronous operation, and handles both absolute and relative paths consistently.
    """

    def __init__(self, cache_file: Union[str, Path] = "checksum_cache.json", base_dir: Union[str, Path, None] = None):
        """
        Initialize the PyChecksumCache with a cache file to store checksums.

        Args:
            cache_file: Path to the JSON file that stores the checksums
            base_dir: Optional base directory for resolving relative paths.
                      If None, the current working directory is used.
        """
        self.cache_file = Path(cache_file)
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.checksums: Dict[str, str] = {}
        self._load_cache()

    def _normalize_path(self, file_path: Union[str, Path]) -> Path:
        """
        Normalize a path, resolving it against the base directory if it's relative.

        Args:
            file_path: The path to normalize

        Returns:
            An absolute Path object
        """
        path = Path(file_path)
        #if not path.is_absolute():
        #    path = (self.base_dir / path).resolve()

        return path

    def _get_cache_key(self, file_path: Union[str, Path]) -> str:
        """
        Get the cache key for a file path.

        Args:
            file_path: The path to get the cache key for

        Returns:
            The cache key (normalized absolute path as string)
        """
        return str(self._normalize_path(file_path))

    def _load_cache(self) -> None:
        """Load MD5 checksums from the cache file if it exists."""
        cache_path = self._normalize_path(self.cache_file)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    self.checksums = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.checksums = {}

    def _save_cache(self) -> None:
        """Save current checksums to the cache file."""
        try:
            # Create directory if it doesn't exist
            cache_path = self._normalize_path(self.cache_file)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_path, 'w') as f:
                json.dump(self.checksums, f, indent=2)
        except IOError as e:
            logger.warning(f"Warning: Failed to save checksum cache: {e}")

    async def _save_cache_async(self) -> None:
        """Save current checksums to the cache file asynchronously."""
        try:
            # Create directory if it doesn't exist
            cache_path = self._normalize_path(self.cache_file)
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            # Use async file IO
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: open(cache_path, 'w').write(json.dumps(self.checksums, indent=2))
            )
        except IOError as e:
            logger.warning(f"Warning: Failed to save checksum cache: {e}")

    def calculate_md5(self, file_path: Union[str, Path]) -> str:
        """
        Calculate MD5 checksum for the given file.

        Args:
            file_path: Path to the file (absolute or relative)

        Returns:
            MD5 hexadecimal digest of the file
        """
        path = self._normalize_path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        md5 = hashlib.md5()

        with open(path, 'rb') as f:
            # Read in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)

        return md5.hexdigest()

    async def calculate_md5_async(self, file_path: Union[str, Path]) -> str:
        """
        Calculate MD5 checksum for the given file asynchronously.

        Args:
            file_path: Path to the file (absolute or relative)

        Returns:
            MD5 hexadecimal digest of the file
        """
        path = self._normalize_path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {path}")

        # Use async file IO to read the file
        loop = asyncio.get_event_loop()
        md5 = hashlib.md5()

        # Open file in binary mode
        file_size = os.path.getsize(path)
        chunk_size = 4096

        with open(path, 'rb') as f:
            for i in range(0, file_size, chunk_size):
                # Run the file read in executor to avoid blocking
                chunk = await loop.run_in_executor(
                    None,
                    lambda: f.read(min(chunk_size, file_size - i))
                )
                if not chunk:
                    break
                md5.update(chunk)

        return md5.hexdigest()

    def has_changed(self, file_path: Union[str, Path]) -> bool:
        """
        Check if the file has changed since the last check.

        Args:
            file_path: Path to the file to check (absolute or relative)

        Returns:
            True if the file is new or has changed, False otherwise
        """
        cache_key = self._get_cache_key(file_path)

        try:
            current_md5 = self.calculate_md5(file_path)
            previous_md5 = self.checksums.get(cache_key)

            if previous_md5 is None or current_md5 != previous_md5:
                self.checksums[cache_key] = current_md5
                self._save_cache()
                return True

            return False

        except FileNotFoundError:
            # If file doesn't exist, remove it from cache
            if cache_key in self.checksums:
                del self.checksums[cache_key]
                self._save_cache()
            return False

    async def has_changed_async(self, file_path: Union[str, Path]) -> bool:
        """
        Check if the file has changed since the last check asynchronously.

        Args:
            file_path: Path to the file to check (absolute or relative)

        Returns:
            True if the file is new or has changed, False otherwise
        """
        cache_key = self._get_cache_key(file_path)

        try:
            current_md5 = await self.calculate_md5_async(file_path)
            previous_md5 = self.checksums.get(cache_key)

            if previous_md5 is None or current_md5 != previous_md5:
                self.checksums[cache_key] = current_md5
                await self._save_cache_async()
                return True

            return False

        except FileNotFoundError:
            # If file doesn't exist, remove it from cache
            if cache_key in self.checksums:
                del self.checksums[cache_key]
                await self._save_cache_async()
            return False

    def execute_if_changed(self, file_path: Union[str, Path], func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute the function only if the file has changed.

        Args:
            file_path: Path to the file to check (absolute or relative)
            func: Function to execute if the file has changed
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result of the function if executed, None otherwise
        """
        if self.has_changed(file_path):
            return func(*args, **kwargs)
        return None

    async def execute_if_changed_async(self, file_path: Union[str, Path], func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute the function (sync or async) only if the file has changed asynchronously.

        Args:
            file_path: Path to the file to check (absolute or relative)
            func: Function or coroutine to execute if the file has changed
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result of the function if executed, None otherwise
        """
        if await self.has_changed_async(file_path):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: func(*args, **kwargs)
                )
        return None

    def any_changed(self, file_list: List[Union[str, Path]]) -> bool:
        """
        Check if any of the specified files have changed.

        Args:
            file_list: List of file paths to check (absolute or relative)

        Returns:
            True if any file has changed, False otherwise
        """
        return any(self.has_changed(file_path) for file_path in file_list)

    async def any_changed_async(self, file_list: List[Union[str, Path]]) -> bool:
        """
        Check if any of the specified files have changed asynchronously.

        Args:
            file_list: List of file paths to check (absolute or relative)

        Returns:
            True if any file has changed, False otherwise
        """
        # Create tasks for all files
        tasks = [self.has_changed_async(file_path) for file_path in file_list]
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        # Return True if any file changed
        return any(results)

    def all_changed(self, file_list: List[Union[str, Path]]) -> bool:
        """
        Check if all of the specified files have changed.

        Args:
            file_list: List of file paths to check (absolute or relative)

        Returns:
            True if all files have changed, False otherwise
        """
        return all(self.has_changed(file_path) for file_path in file_list)

    async def all_changed_async(self, file_list: List[Union[str, Path]]) -> bool:
        """
        Check if all of the specified files have changed asynchronously.

        Args:
            file_list: List of file paths to check (absolute or relative)

        Returns:
            True if all files have changed, False otherwise
        """
        # Create tasks for all files
        tasks = [self.has_changed_async(file_path) for file_path in file_list]
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        # Return True if all files changed
        return all(results)

    def execute_if_any_changed(self, file_list: List[Union[str, Path]], func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute the function if any of the specified files have changed.

        Args:
            file_list: List of file paths to check (absolute or relative)
            func: Function to execute if any file has changed
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result of the function if executed, None otherwise
        """
        if self.any_changed(file_list):
            return func(*args, **kwargs)
        return None

    async def execute_if_any_changed_async(self, file_list: List[Union[str, Path]], func: Callable, *args, **kwargs) -> Optional[Any]:
        """
        Execute the function if any of the specified files have changed asynchronously.

        Args:
            file_list: List of file paths to check (absolute or relative)
            func: Function or coroutine to execute if any file has changed
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result of the function if executed, None otherwise
        """
        if await self.any_changed_async(file_list):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: func(*args, **kwargs)
                )
        return None

    def refresh_cache(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """
        Recalculate the checksum and update the cache.

        Args:
            file_path: Path to the file to refresh (absolute or relative),
                     or None to refresh all files in the cache
        """
        if file_path is None:
            # Make a copy of keys to avoid modifying during iteration
            for path in list(self.checksums.keys()):
                try:
                    self.checksums[path] = self.calculate_md5(path)
                except FileNotFoundError:
                    del self.checksums[path]
        else:
            cache_key = self._get_cache_key(file_path)
            try:
                self.checksums[cache_key] = self.calculate_md5(file_path)
            except FileNotFoundError:
                if cache_key in self.checksums:
                    del self.checksums[cache_key]

        self._save_cache()

    async def refresh_cache_async(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """
        Recalculate the checksum and update the cache asynchronously.

        Args:
            file_path: Path to the file to refresh (absolute or relative),
                     or None to refresh all files in the cache
        """
        if file_path is None:
            # Make a copy of keys to avoid modifying during iteration
            tasks = []
            for path in list(self.checksums.keys()):
                tasks.append(self._refresh_single_file_async(path))
            await asyncio.gather(*tasks)
        else:
            cache_key = self._get_cache_key(file_path)
            try:
                self.checksums[cache_key] = await self.calculate_md5_async(file_path)
            except FileNotFoundError:
                if cache_key in self.checksums:
                    del self.checksums[cache_key]

        await self._save_cache_async()

    async def _refresh_single_file_async(self, file_path: str) -> None:
        """Helper method to refresh a single file asynchronously."""
        try:
            self.checksums[file_path] = await self.calculate_md5_async(file_path)
        except FileNotFoundError as e:
            logger.info(f"File not found: {file_path}")
            if file_path in self.checksums:
                del self.checksums[file_path]

    def clear_cache(self) -> None:
        """Clear the entire cache."""
        self.checksums = {}
        self._save_cache()

    async def clear_cache_async(self) -> None:
        """Clear the entire cache asynchronously."""
        self.checksums = {}
        await self._save_cache_async()

    def remove_from_cache(self, file_path: Union[str, Path]) -> None:
        """
        Remove a specific file from the cache.

        Args:
            file_path: Path to the file to remove from the cache (absolute or relative)
        """
        cache_key = self._get_cache_key(file_path)
        if cache_key in self.checksums:
            del self.checksums[cache_key]
            self._save_cache()

    async def remove_from_cache_async(self, file_path: Union[str, Path]) -> None:
        """
        Remove a specific file from the cache asynchronously.

        Args:
            file_path: Path to the file to remove from the cache (absolute or relative)
        """
        cache_key = self._get_cache_key(file_path)
        if cache_key in self.checksums:
            del self.checksums[cache_key]
            await self._save_cache_async()

    def transform(self,
                  input_files: List[Union[str, Path]],
                  output_folder: Union[str, Path],
                  output_extension: str = "",
                  transform_func: Callable[[str, str], Any] = None,
                  force: bool = False) -> List[Tuple[Path, bool]]:
        """
        Transform input files only if they've changed and save to output folder.

        Args:
            input_files: List of input file paths to process (absolute or relative)
            output_folder: Folder to save the transformed output (absolute or relative)
            output_extension: Optional extension to add/replace for output files
            transform_func: Function that performs the transformation
                           Should accept (input_path, output_path) as arguments
            force: If True, process all files regardless of whether they've changed

        Returns:
            List of tuples containing (output_path, was_transformed)
        """
        # Ensure output folder exists
        output_path = self._normalize_path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        results = []

        # Default transformation function (copy file) if none provided
        if transform_func is None:
            transform_func = shutil.copy2

        for input_file in input_files:
            input_path = self._normalize_path(input_file)

            # Generate output filename
            if output_extension:
                if output_extension.startswith('.'):
                    # Replace extension
                    output_filename = input_path.stem + output_extension
                else:
                    # Append to existing name
                    output_filename = input_path.name + output_extension
            else:
                output_filename = input_path.name

            output_file = output_path / output_filename

            # Check if processing is needed
            needs_processing = force or self.has_changed(input_path)

            if needs_processing:
                # Perform the transformation
                transform_func(str(input_path), str(output_file))

            results.append((output_file, needs_processing))

        return results

    async def transform_async(self,
                              input_files: List[Union[str, Path]],
                              output_folder: Union[str, Path],
                              output_extension: str = "",
                              transform_func: Callable[[str, str], Any] = None,
                              force: bool = False,
                              concurrency_limit: int = 10) -> List[Tuple[Path, bool]]:
        """
        Transform input files asynchronously only if they've changed and save to output folder.

        Args:
            input_files: List of input file paths to process (absolute or relative)
            output_folder: Folder to save the transformed output (absolute or relative)
            output_extension: Optional extension to add/replace for output files
            transform_func: Function or coroutine that performs the transformation
                           Should accept (input_path, output_path) as arguments
            force: If True, process all files regardless of whether they've changed
            concurrency_limit: Maximum number of concurrent transformations

        Returns:
            List of tuples containing (output_path, was_transformed)
        """
        # Ensure output folder exists
        output_path = self._normalize_path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        # Default transformation function (copy file) if none provided
        if transform_func is None:
            transform_func = shutil.copy2

        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrency_limit)

        # Process files with concurrency limit
        async def process_file(input_file):
            input_path = self._normalize_path(input_file)

            # Generate output filename
            if output_extension:
                if output_extension.startswith('.'):
                    # Replace extension
                    output_filename = input_path.stem + output_extension
                else:
                    # Append to existing name
                    output_filename = input_path.name + output_extension
            else:
                output_filename = input_path.name

            output_file = output_path / output_filename

            # Check if processing is needed
            needs_processing = force or await self.has_changed_async(input_path)

            if needs_processing:
                # Acquire semaphore to limit concurrency
                async with semaphore:
                    # Perform the transformation
                    if asyncio.iscoroutinefunction(transform_func):
                        await transform_func(str(input_path), str(output_file))
                    else:
                        # Run synchronous function in executor
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            lambda: transform_func(str(input_path), str(output_file))
                        )

            return (output_file, needs_processing)

        # Create tasks for all files
        tasks = [process_file(input_file) for input_file in input_files]

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)

        return results