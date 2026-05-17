#!/usr/bin/env python3
"""Migration script to move config files to ~/.config/ytm-cli/"""

import shutil
from pathlib import Path


def migrate_config_files():
    """Move config files from project root to ~/.config/ytm-cli/"""
    old_config_dir = Path(__file__).parent
    new_config_dir = Path.home() / ".config" / "ytm-cli"

    # Create new config directory
    new_config_dir.mkdir(parents=True, exist_ok=True)

    files_to_migrate = [
        "config.ini",
        "dislikes.json",
    ]

    migrated = []

    for filename in files_to_migrate:
        old_file = old_config_dir / filename
        new_file = new_config_dir / filename

        if old_file.exists() and not new_file.exists():
            print(f"Moving {filename} to ~/.config/ytm-cli/...")
            shutil.copy2(old_file, new_file)
            migrated.append(filename)
        elif old_file.exists() and new_file.exists():
            print(f"Skipping {filename} (already exists in new location)")

    # Migrate playlists directory
    old_playlists = old_config_dir / "playlists"
    new_playlists = new_config_dir / "playlists"

    if old_playlists.exists() and not new_playlists.exists():
        print("Moving playlists/ to ~/.config/ytm-cli/...")
        shutil.copytree(old_playlists, new_playlists)
        migrated.append("playlists/")

    if migrated:
        print("\n✅ Migration complete! The following files were moved:")
        for f in migrated:
            print(f"  - {f}")
        print(f"\nYour config files are now in: {new_config_dir}")
        print("You can safely delete the old files from the project root.")
    else:
        print("No files to migrate. All config files are already in the new location.")


if __name__ == "__main__":
    migrate_config_files()
