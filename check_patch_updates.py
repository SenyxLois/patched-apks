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
            "rvx_patches_version": None,
            "revanced_patches_version": None,
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
    
    # Check RVX Patches
    print("\n[1/3] Checking RVX Patches (inotia00)...")
    rvx_latest = fetch_latest_release_version("inotia00/revanced-patches")
    rvx_version = rvx_latest['version']
    
    if current_versions['rvx_patches_version'] is None:
        print(f"  → First run: RVX patches version = {rvx_version}")
        updates_available = True
    elif current_versions['rvx_patches_version'] != rvx_version:
        print(f"  ✓ NEW VERSION AVAILABLE!")
        print(f"    Current: {current_versions['rvx_patches_version']}")
        print(f"    Latest:  {rvx_version}")
        print(f"    Release: {rvx_latest['release_url']}")
        updates_available = True
    else:
        print(f"  • Up to date: {rvx_version}")
    
    new_versions['rvx_patches_version'] = rvx_version
    new_versions['rvx_patches_updated'] = rvx_latest['published_at']
    
    # Check ReVanced Patches
    print("\n[2/3] Checking ReVanced Patches...")
    revanced_latest = fetch_latest_release_version("ReVanced/revanced-patches")
    revanced_version = revanced_latest['version']
    
    if current_versions['revanced_patches_version'] is None:
        print(f"  → First run: ReVanced patches version = {revanced_version}")
        updates_available = True
    elif current_versions['revanced_patches_version'] != revanced_version:
        print(f"  ✓ NEW VERSION AVAILABLE!")
        print(f"    Current: {current_versions['revanced_patches_version']}")
        print(f"    Latest:  {revanced_version}")
        print(f"    Release: {revanced_latest['release_url']}")
        updates_available = True
    else:
        print(f"  • Up to date: {revanced_version}")
    
    new_versions['revanced_patches_version'] = revanced_version
    new_versions['revanced_patches_updated'] = revanced_latest['published_at']
    
    # Check Revanced CLI
    print("\n[3/3] Checking Revanced CLI...")
    cli_latest = fetch_latest_release_version("inotia00/revanced-cli")
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
            f.write(f"RVX_PATCHES_VERSION={new_versions['rvx_patches_version']}\n")
            f.write(f"REVANCED_PATCHES_VERSION={new_versions['revanced_patches_version']}\n")
            f.write(f"CLI_VERSION={new_versions['cli_version']}\n")
        print(f"\n✓ Set GitHub Actions output variables")
    
    # Also set in GitHub ENV for workflow use
    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a') as f:
            f.write(f"UPDATES_AVAILABLE={'true' if updates_available else 'false'}\n")
            f.write(f"RVX_PATCHES_VERSION={new_versions['rvx_patches_version']}\n")
            f.write(f"REVANCED_PATCHES_VERSION={new_versions['revanced_patches_version']}\n")
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
