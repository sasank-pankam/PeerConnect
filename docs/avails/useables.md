# Useables

Variety of utility functions and helper methods that facilitate common tasks across the code.

## Key Functions

- **func_str(func_name):**  
  Returns a string representation of a function’s name and its source file path.

- **get_unique_id(_type):**  
  Generates a unique identifier as either a UUID in string or byte format.

- **shorten_path(path, max_length):**  
  Shortens a filesystem path to fit within a specified maximum length.

- **recv_int(get_bytes, type):**  
  Asynchronously receives a specified number of bytes and unpacks them as an integer.

- **get_timeouts(initial, factor, max_retries, max_value):**  
  Generates exponential backoff timeout values for retry operations.

- **async_timeouts(...):**  
  An asynchronous generator that yields timeout values with delays.

- **echo_print(...):**  
  A wrapper for the built-in print function that includes terminal color resets.

- **async_input(helper_str):**  
  Asynchronously waits for user input.

- **open_file(content):**  
  Opens a file using the system’s default application (platform-specific implementation).

- **wait_for_sock_read and wait_for_sock_write:**  
  Utility functions that use `select` to wait for a socket to be ready for reading or writing.

- **from_coroutine, sync, and awaitable:**  
  Functions and decorators to bridge synchronous and asynchronous function calls.

- **spawn_task:**  
  Wraps a function call into an `asyncio` task with exception handling.

- **search_relevant_peers(peer_list, search_string):**  
  Iterates over a list of peers to find those matching a given search string.

## Constants

- **COLORS and COLOR_RESET:**  
  Terminal color codes for formatting output.

## Purpose

- Provides essential utilities for async operations and system interaction.

- Encapsulates many of the "helper" routines needed throughout the system to manage asynchronous operations, formatting, and other common programming tasks.

[back](/docs/avails)
