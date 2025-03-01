# Custom Exceptions

## Core Exceptions

- `DispatcherFinalizing`: Dispatcher shutting down
  - Indicates that the dispatcher is finalizing and is no longer processing events.

- `WebSocketRegistryReStarted`: Websocket restart attempt
  - Signals that the WebSocket registry has been restarted, potentially disrupting ongoing operations.

- `InvalidPacket`: Malformed network data
  - Raised when an incoming packet is ill-formed or does not meet protocol requirements.

- `TransferIncomplete`: Interrupted data transfer
  - Used to indicate that a file or data transfer was paused or broken midway.

- `ResourceBusy`: Contention on locked resource
  - Indicates that a resource is currently busy; it includes an attribute (`available_after`) that holds an `asyncio.Condition` to notify when the resource may be available.

- `TransferRejected`: ...
  - Raised when a data transfer request is rejected.

- `CancelTransfer`: ...
  - Signals a request to cancel an ongoing transfer.

## Network Errors

- `CannotConnect`: Connection failure
  - A subclass of `OSError` indicating that a connection to a provided address or peer could not be established.

- `UnknownConnectionType`: Unrecognized connection
  - Indicates that an unknown or unsupported type of connection has been encountered.

## State Errors

- `InvalidStateError`: Invalid operation for current state
  - Raised when an operation is attempted in an invalid state.

## Purpose

Domain-specific error types for improved error handling.

[back](/docs/avails)
