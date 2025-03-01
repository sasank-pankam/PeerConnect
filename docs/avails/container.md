# src/avails/container.py

Provides simple container classes in the system for managing peers and file transfers. The main components include:

## PeerDict

- **Purpose:**  
  A subclass of Python’s built-in dictionary that is specialized to store peer objects (keyed by a unique peer identifier).
- **Key Methods:**  
  - `get_peer(peer_id)`: Retrieves a peer by its ID.
  - `add_peer(peer_obj)`: Adds a new peer to the dictionary.
  - `extend(iterable_of_peer_objects)`: Adds multiple peers at once.
  - `remove_peer(peer_id)`: Removes a peer based on its ID.
  - `peers()`: Returns an iterable view of the stored peer objects.

## TransfersBookKeeper

- **Purpose:**  
  Manages file or directory transfer handles and keeps track of transfers in different states:
  - **Current Transfers:** Active transfers.
  - **Continued Transfers:** Transfers that have been paused or are intended to be resumed.
  - **Completed Transfers:** Transfers that have finished.
  - **Scheduled Transfers:** Transfers that are planned but not yet started.
- **Features:**  
  - Uses internal dictionaries and sets to maintain a mapping of peer IDs to their transfer handles.
  - Provides methods to add a transfer to different states and to retrieve or move transfers as needed.
  - Includes a class method `get_new_id()` to generate unique identifiers for transfers. [DEP](/docs/README.md#legend)

Abstracts the management of peers and transfers, simplifying how these entities are stored and retrieved across the application.

[back](/docs/avails)
