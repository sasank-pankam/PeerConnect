# Handlesignals Module

[src.conduit.handlesignals](/src/conduit/handlesignals.py)

## FrontEndSignalDispatcher

```python
class FrontEndSignalDispatcher(BaseDispatcher)
```

Handles system-level signaling

**Registered Handlers:**

- Peer connections
- Profile synchronization
- User searches
- Peer list management
- sync_users ([WIP](/docs/README.md#legend))

**Key Functions:**

### Connect Peer

```python
async def connect_peer(handle_data: DataWeaver):
```

**associated header** : [HANDLE](/src/conduit/headers).CONNECT_USER

### Search For User

```python
async def search_for_user(data: DataWeaver)
```

**associated header** : [HANDLE](/src/conduit/headers).SEARCH_FOR_NAME

Initiates peer search by name

- Parameters: Search string in DataWeaver.content
- Returns: List of matching peers

### Align Profiles

see [handleprofiles](/docs/conduit/handleprofiles.md#align-profiles)

**associated header** : [HANDLE](/src/conduit/headers).SEND_PROFILES

### Send List

```python
async def send_list(data: DataWeaver):
```

**associated header** : [HANDLE](/src/conduit/headers).SEND_PEER_LIST

Manages peer list requests

---

[back](/docs/conduit)
