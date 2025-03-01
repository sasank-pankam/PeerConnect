# src/avails/constants.py

> Recommended standard for importing this module

```py
from src.avails import const
```

Defines various constants that configure and control the behavior of the PeerConnect system. The constants include:

- **Application and Logging Settings:**  
  - `APP_NAME`: Name of the application.
  - `CLEAR_LOGS`, `USERNAME`: Configuration values.
  
- **Networking Constants:**  
  - Default IP addresses (`SERVER_IP`, `MULTICAST_IP_v4`, `MULTICAST_IP_v6`, `BROADCAST_IP`).
  - Bind IP addresses for IPv4 and IPv6.
  - Port numbers for different services (e.g., `PORT_THIS`, `PORT_REQ`, `PORT_SERVER`, etc.).
  - IP version and flags (`USING_IP_V4`, `USING_IP_V6`).

- **File and Path Settings:**  
  - File paths for downloads, logs, configurations, and profiles using Python’s `Path` utility.

- **Timeouts and Limits:**  
  - Timeout settings (`SERVER_TIMEOUT`, `DEFAULT_TRANSFER_TIMEOUT`, etc.).
  - Limits such as maximum connections, message buffer lengths, and datagram sizes.
- **Ports:**
  - `PORT_THIS`,`PORT_REQ`,`PORT_NETWORK`,`PORT_SERVER`,`PORT_PAGE`,`PORT_PAGE_SERVE`
  
- **Miscellaneous:**  
  - Constants related to data types and transfer units (e.g., `BYTES_PER_KB`, `RATE_WINDOW`).
  - Flags for operating system checks (e.g., `IS_WINDOWS`, `IS_LINUX`, `IS_DARWIN`).

These constants are used throughout the package to ensure consistency in configuration and to simplify modifications to core settings.

[back](/docs/avails)
