#!/usr/bin/env python3
"""
Version comparison script to detect new patches
Compares stored patch versions with latest releases from GitHub APIs
"""

import json
import requests
import os
import sys
from datetime import datetime


def load_version_file(filepath='patch_versions.json'):
    """Load previously stored patch versions"""
    if not os.path.exists(filepath):
        print(f"Version file {filepath} not found. This is the first run.")
        return {
            "morphe_patches_version": None,
            "photos_patches_version": None,
            "cli_version": None,
            "last_updated": None,
            "last_release_tag": None
        }
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON in {filepath}")
        sys.exit(1)


def save_version_file(data, filepath='patch_versions.json'):
    """Save current patch versions to file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved version info to {filepath}")


def fetch_latest_release_version(repo):
    """Fetch latest release version from GitHub API"""
    try:
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Extract version from tag_name
        tag_name = data.get('tag_name', '')
        version = tag_name.lstrip('v')
        published_at = data.get('published_at', '')
        
        return {
            'version': version,
            'tag': tag_name,
            'published_at': published_at,
            'release_url': data.get('html_url', '')
        }
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch latest release from {repo}: {e}")
        sys.exit(1)


def check_for_updates(current_versions):
    """Check all patch sources for updates"""
    updates_available = False
    new_versions = current_versions.copy()
    
    print("=" * 60)
    print("Checking for Patch Updates")
    print("=" * 60)
    
    # Check Morphe Patches (YouTube Music)
    print("\n[1/3] Checking Morphe Patches (YouTube Music)...")
    morphe_latest = fetch_latest_release_version("MorpheApp/morphe-patches")
    morphe_version = morphe_latest['version']
    
    if current_versions['morphe_patches_version'] is None:
        print(f"  → First run: Morphe patches version = {morphe_version}")
        updates_available = True
    elif current_versions['morphe_patches_version'] != morphe_version:
        print(f"  ✓ NEW VERSION AVAILABLE!")
        print(f"    Current: {current_versions['morphe_patches_version']}")
        print(f"    Latest:  {morphe_version}")
        print(f"    Release: {morphe_latest['release_url']}")
        updates_available = True
    else:
        print(f"  • Up to date: {morphe_version}")
    
    new_versions['morphe_patches_version'] = morphe_version
    new_versions['morphe_patches_updated'] = morphe_latest['published_at']
    
    # Check Google Photos Patches (rushiranpise fork)
    print("\n[2/3] Checking Google Photos Patches (rushiranpise fork)...")
    photos_latest = fetch_latest_release_version("rushiranpise/morphe-patches")
    photos_version = photos_latest['version']
    
    if current_versions['photos_patches_version'] is None:
        print(f"  → First run: Google Photos patches version = {photos_version}")
        updates_available = True
    elif current_versions['photos_patches_version'] != photos_version:
        print(f"  ✓ NEW VERSION AVAILABLE!")
        print(f"    Current: {current_versions['photos_patches_version']}")
        print(f"    Latest:  {photos_version}")
        print(f"    Release: {photos_latest['release_url']}")
        updates_available = True
    else:
        print(f"  • Up to date: {photos_version}")
    
    new_versions['photos_patches_version'] = photos_version
    new_versions['photos_patches_updated'] = photos_latest['published_at']
    
    # Check Morphe CLI
    print("\n[3/3] Checking Morphe CLI...")
    cli_latest = fetch_latest_release_version("MorpheApp/morphe-desktop")
    cli_version = cli_latest['version']
    
    if current_versions['cli_version'] is None:
        print(f"  → First run: CLI version = {cli_version}")
        updates_available = True
    elif current_versions['cli_version'] != cli_version:
        print(f"  ✓ NEW VERSION AVAILABLE!")
        print(f"    Current: {current_versions['cli_version']}")
        print(f"    Latest:  {cli_version}")
        print(f"    Release: {cli_latest['release_url']}")
        updates_available = True
    else:
        print(f"  • Up to date: {cli_version}")
    
    new_versions['cli_version'] = cli_version
    new_versions['cli_updated'] = cli_latest['published_at']
    new_versions['last_updated'] = datetime.now().isoformat()
    
    print("\n" + "=" * 60)
    
    return updates_available, new_versions


def set_github_output(updates_available, new_versions):
    """Set GitHub Actions output variables"""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"UPDATES_AVAILABLE={'true' if updates_available else 'false'}\n")
            f.write(f"MORPHE_PATCHES_VERSION={new_versions['morphe_patches_version']}\n")
            f.write(f"PHOTOS_PATCHES_VERSION={new_versions['photos_patches_version']}\n")
            f.write(f"CLI_VERSION={new_versions['cli_version']}\n")
        print(f"\n✓ Set GitHub Actions output variables")
    
    # Also set in GitHub ENV for workflow use
    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a') as f:
            f.write(f"UPDATES_AVAILABLE={'true' if updates_available else 'false'}\n")
            f.write(f"MORPHE_PATCHES_VERSION={new_versions['morphe_patches_version']}\n")
            f.write(f"PHOTOS_PATCHES_VERSION={new_versions['photos_patches_version']}\n")
            f.write(f"CLI_VERSION={new_versions['cli_version']}\n")


def main():
    # Load current stored versions
    current_versions = load_version_file()
    
    # Check for updates
    updates_available, new_versions = check_for_updates(current_versions)
    
    # Save new versions
    save_version_file(new_versions)
    
    # Set GitHub Actions outputs
    set_github_output(updates_available, new_versions)
    
    # Output summary
    if updates_available:
        print("\n🎉 New patches are available! Workflow will proceed with patching.")
        sys.exit(0)
    else:
        print("\n✓ All patches are up to date. Skipping build.")
        sys.exit(1)  # Exit with code 1 to signal no update needed (can be used to skip workflow)


if __name__ == "__main__":
    main()
