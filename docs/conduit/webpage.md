# Webpage Module

[src.conduit.webpage](/src/conduit/webpage.py)

**Frontend Interaction API**: Wraps [DataWeaver](/docs/avails/wire.md#dataweaver)

```python
async def ask_for_interface_choice(interfaces)
```

Requests network interface selection from user

- Parameters: List of available interfaces
- Returns: Selected interface ID

```python
async def update_peer(peer)
```

Updates peer status in UI

- Parameters: RemotePeer object
- Sends: ONLINE/OFFLINE status

```python
async def transfer_update(peer_id, transfer_id, file_item)
```

Sends file transfer progress updates

- Parameters:
  - peer_id: Target peer
  - transfer_id: Transfer session ID
  - file_item: Transfer metadata

```python
async def search_response(search_id, peer_list)
```

Returns search results to frontend

- Parameters:
  - search_id: Original request ID
  - peer_list: List of RemotePeer objects

---

## Data Structures

### `DataWeaver`

```python
class DataWeaver()
```

Standard message format for frontend communication

**Structure:**

```python
{
    "header": str,       # Operation type
    "content": dict,     # Payload data
    "peer_id": str,      # Target peer ID
    "msg_id": str        # Message identifier
}
```

For more details on wire formats see [avails.wire](/docs/avails/wire.md)

---

[back](/docs/conduit/)
