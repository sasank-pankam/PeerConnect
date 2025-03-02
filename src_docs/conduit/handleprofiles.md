# Handleprofiles Module

[src.conduit.handleprofiles](/src/conduit/handleprofiles.py)

**Profile Management**: all the profile level interactions with UI

## Key Functions

### Align Profiles

```python
async def align_profiles(_: DataWeaver)
```

Synchronizes profiles with frontend

- Sends profile data
- Receives updated configurations

### Configure Further Profile Data

```python
async def configure_further_profile_data(profiles_data)
```

Processes profile updates from UI

- Handles:
  - Profile deletions
  - New profile creation
  - Existing profile updates

### Set Selected Profile

```python
async def set_selected_profile(page_data: DataWeaver)
```

Sets active application profile

- Parameters: DataWeaver with profile data

---

[back](/src_docs/conduit)
