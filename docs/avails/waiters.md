# Thread Control Utilities

**[DEP](/docs/README.md#legend)**: No longer in use

## Abstract
>
> ```python
> class _ThreadActuator
>    ```
>
> ### Features
>
> - Cross-platform select() wake mechanism
> - Control flag for thread termination
> - File descriptor integration
>
> ### Methods
>
> - `wake()`: Interrupts blocking select()
> - `signal_stopping()`: Initiate graceful shutdown
> - `fileno()`: Integration with select()
>
> ### Platform Support
>
> - Windows: Uses socketpair()
> - Linux/macOS: Uses os.pipe()

## Key Functions

- **_waker_flag_windows() and _waker_flag_linux():**  
  Platform-specific implementations that create a pair of file descriptors (or socket pairs) for waking up blocking `select` calls:
  - On Windows: Uses `socket.socketpair()` and wraps file descriptors with file objects.
  - On Linux (and other platforms): Uses `os.pipe()`.

## _ThreadActuator Class

- **Purpose:**  
  Provides a mechanism to control threads in a blocking context, especially for waking up `select` operations.
- **Attributes:**
  - `control_flag`: A boolean flag indicating the state.
  - `reader`: A file-like object used for monitoring via `select`.
  - `waker`: A file-like object used to send a wake-up signal.
- **Methods:**
  - `wake()`: Writes a byte to the waker, forcing a wake-up in blocking calls.
  - `flip()`: Toggles the internal control flag, which can be used to change state during loops.

## Purpose

- Crucial for integrating non-blocking asynchronous I/O with lower-level system calls that traditionally rely on blocking operations.

- Enables clean thread termination and I/O multiplexing control.

[back](/docs/avails)
