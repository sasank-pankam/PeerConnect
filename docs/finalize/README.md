# Application Finalizing Sequence

* **User Requested**:
  1. Command from UI arrives to websocket endpoint.
  2. Application sets a finalizing flag that commands application services to stop their tasks. [more](/docs/core/README.md)
  3. Event Loop Finalizes. [more](/docs/core/README.md)

* **SIGINT or SIGTERM** :
  1. cpython runs a signal handler registered by asyncio's runner
  2. Application callback runs a routine that sets finalizing flag. [more](/docs/finalize/README.md)
  3. Application services smooth stop their functioning. [more](/docs/finalize/README.md)
