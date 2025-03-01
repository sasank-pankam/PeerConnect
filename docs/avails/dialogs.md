# Dialog Handlers

Platform-independent file/directory selection dialogs.

## Implementations

### TkDialogs

```python
class TkDialogs(IDialogs)
```

- Uses Tkinter for GUI dialogs
- Maintains recent directory state

### FileExplorerDialog

```python
class FileExplorerDialog(IDialogs)
```

- Uses native system dialogs via subprocess
- Supports Windows, macOS, and Linux (requires zenity)

## Usage

```python
get_dialog_handler() -> IDialogs

```

Returns appropriate dialog implementation based on environment capabilities.

[back](/docs/avails)
