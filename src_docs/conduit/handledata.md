# Handledata Module

[src.conduit.handledata](/src/conduit/handledata.py)

**User Interaction Operations**: associated with user interactions

## `FrontEndDataDispatcher`

```python
class FrontEndDataDispatcher(BaseDispatcher)
```

Handles data operations between backend and frontend

**Methods:**

- `submit(data_weaver)`: Processes incoming data packets
- `register_all()`: Registers command handlers for:
  - Directory transfers
  - File transfers
  - Text messages
  - Batch file operations

**Key Functions:**

## New Dir Transfer

```python
async def new_dir_transfer(command_data: DataWeaver)
```

**associated header** : [HANDLE](/src/conduit/headers).SEND_DIR

Handles directory transfer initialization

- Parameters: DataWeaver with 'path' in content
- Manages directory selection and peer connection

## Send File

```python
async def send_file(command_data: DataWeaver)
```

**associated header** : [HANDLE](/src/conduit/headers).SEND_FILE

Manages file transfer workflow

- Handles single/multiple file selection
- Parameters: DataWeaver with 'paths' list

## Send Text

```python
async def send_text(command_data: DataWeaver)
```

**associated header** : [HANDLE](/src/conduit/headers).SEND_TEXT

Processes text message transmission

- Requires peer connection
- Uses WireData for message formatting

## Send Files To Multiple Peers

```python
async def send_files_to_multiple_peers(command_data: DataWeaver):
```

**associated header** : [HANDLE](/src/conduit/headers).SEND_FILE_TO_MULTIPLE_PEERS

- Uses [OTM](/src_docs/transfer/otm.md) transfer to complete transfer

[WIP](/src_docs/README.md#legend)

---

[back](/src_docs/conduit)
