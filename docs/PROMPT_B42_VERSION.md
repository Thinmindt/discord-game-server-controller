# Project Zomboid B42 Version Toggle Implementation

## Overview

Add the ability to toggle Project Zomboid server between stable (Build 41) and beta (Build 42) versions via Discord commands.

## Background

Project Zomboid Build 42 is currently in beta and requires opting into the `b42unstable` Steam beta branch. The server needs to:

1. Be stopped before switching versions
2. Run SteamCMD with the appropriate beta flag
3. Handle the fact that B41 and B42 saves are **not compatible**

## Requirements

### 1. New Discord Command: `!version`

Display the current PZ server version:

```
!version pz
```

Response should show:

- Current version/build number
- Whether running stable (B41) or beta (B42)

### 2. New Discord Command: `!setversion`

Switch between stable and beta versions:

```
!setversion pz stable
!setversion pz beta
!setversion pz b41
!setversion pz b42
```

#### Behavior:

- **Require server to be stopped** before switching
- **Update Local State:** Persist the selected version (e.g., in `pz_version_state.json`) so the correct server name is used on restart.
- **Server Name Isolation:**
  - Use different server names for each version to isolate saves and configs (e.g., `servertest` for Stable, `servertest_b42` for Beta).
  - This prevents B42 configs/saves from corrupting B41 files and vice-versa.
- Run SteamCMD with appropriate flags:
  - Stable: No beta flag (or `+app_update 380870 validate`)
  - Beta: `+app_update 380870 -beta b42unstable validate`
- Show progress messages during update
- Warn user that saves are separate for each version.
- **If already on the requested branch:** Skip SteamCMD update and confirm the current version instead.

### 3. Auto-Backup Before Version Switch

Before switching versions, automatically create a backup:

- Use the existing `BackupUtility` class
- Name the backup to indicate it's a pre-version-switch backup
- Include the current version in the backup folder name (e.g., `PZ_PreSwitch_B41_2026-01-03_14-30-00`)
- **Version-Specific Backup Folders:** Each version's backups go into separate subfolders:
  - `PZ_BACKUP_PATH/stable/` for B41 backups
  - `PZ_BACKUP_PATH/beta/` for B42 backups
- This keeps backup history organized and version-specific.

### 4. Version Detection & State Management

- **State File:** Maintain a `pz_version_state.json` file in the **PZ server directory** (`PZ_SERVER_PATH`).
  ```json
  {
    "current_branch": "stable",
    "last_updated": "2026-01-03T12:00:00"
  }
  ```
- **Server Name Logic:**
  - If branch is `stable`: Use `PZ_SERVER_NAME` (default: `servertest`)
  - If branch is `beta`: Use `PZ_SERVER_NAME + "_b42"` (e.g., `servertest_b42`)
- **Verification:**
  - Parse server logs for version string to confirm the running version matches the expected state.

### 5. First-Time Version Setup (Config Handling)

When switching to a version for the first time (e.g., first switch to B42):

1. **Let Project Zomboid generate a fresh default config** - Do not auto-copy the old config.
2. **Inform the user** that a new config was generated and they may want to copy settings (admin password, server name, etc.) from the previous version's config.
3. **Provide guidance** on config file locations:
   - Stable config: `Zomboid/Server/servertest.ini`
   - Beta config: `Zomboid/Server/servertest_b42.ini`

### 6. New Discord Command: `!available_versions`

Display the supported PZ server versions:

```
!available_versions pz
```

Response should show a static list:

- `stable` (Build 41) - Current stable release
- `beta` (Build 42) - Unstable beta branch

Indicates which version is currently selected.

### 7. Configuration

Add to `.env.example`:

```dotenv
# Beta branch name for B42 (default: b42unstable)
PZ_BETA_BRANCH=b42unstable
```

## Implementation Notes

### SteamCMD Commands

**Update to stable:**

```
steamcmd +login anonymous +app_update 380870 validate +quit
```

**Update to beta:**

```
steamcmd +login anonymous +app_update 380870 -beta b42unstable validate +quit
```

### Files to Modify

1. `src/project_zomboid_manager.py`:

   - Add `get_version()` method
   - Add `set_version(branch: str)` method
   - Version detection logic

2. `src/game_server_interface.py`:

   - Add optional `get_version()` to interface
   - Add optional `set_version()` to interface

3. `src/game_commands.py`:

   - Add `cmd_version()` handler
   - Add `cmd_setversion()` handler
   - Add `cmd_available_versions()` handler

4. `main.py`:

   - Add `!version` command
   - Add `!setversion` command
   - Add `!available_versions` command

5. `src/config.py`:

   - Add `PZ_BETA_BRANCH` config

6. `.env.example`:
   - Document new config option

### Error Handling

- Server must be stopped before version switch
- Validate beta branch name
- Handle SteamCMD failures gracefully
- Warn about save incompatibility

### Testing

Create tests in `test/test_pz_version.py`:

- Test version detection
- Test SteamCMD command generation
- Test error cases (server running, invalid branch)

## Code Quality

After implementation, ensure:

```bash
ruff format .
ruff check .
mypy .
pytest
```

All checks should pass with no errors.

## Questions to Consider

1. Should we support custom beta branch names beyond `b42unstable`?

- no, not now

2. Should we store the current branch selection somewhere to persist across restarts?

- yes

3. Should `!update` use the currently selected branch, or always use stable?

- Use the currently selected branch.
- **Auto-backup before updating** (same as version switch).
- Backups go into the version-specific subfolder (`stable/` or `beta/`).

4. Do we want a command to list available versions?

- Yes, use `!available_versions` command.
- Shows a static list of supported versions (stable and beta).
- Indicates which version is currently selected.

5. What happens when switching to a version for the first time?

- Let Project Zomboid generate a fresh default config.
- Inform the user they can manually copy settings (password, etc.) from the old config.
- Do NOT auto-copy configs to avoid compatibility issues.

6. Are saves independent between versions?

- Yes, saves are completely independent.
- Switching versions does NOT affect the other version's save.
- Make this clear in user-facing messages.

7. What if the server is already on the requested branch?

- Skip the SteamCMD update.
- Confirm that the server is already on the correct version.
