import json
import requests
import os
import sys
from collections import defaultdict


def load_enabled_patches(filepath='YTMusic-patch.json'):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Handle different formats
        enabled_patch_names = []
        
        if isinstance(data, list):
            # Check if it's a list of strings or objects
            if data and isinstance(data[0], str):
                # List of patch names
                enabled_patch_names = data
                print(f"Loaded {len(enabled_patch_names)} patch names from {filepath}")
            elif data and isinstance(data[0], dict):
                # List of patch objects
                for patch in data:
                    if patch.get("use", False):
                        compat_packages = patch.get("compatiblePackages", {})
                        # Check if this patch supports YouTube Music
                        if "com.google.android.apps.youtube.music" in compat_packages:
                            enabled_patch_names.append(patch.get("name"))
                print(f"Loaded {len(enabled_patch_names)} enabled YouTube Music patches from {filepath}")
        elif isinstance(data, dict):
            # Might be a dict with patch names as keys
            enabled_patch_names = list(data.keys())
            print(f"Loaded {len(enabled_patch_names)} patch names from {filepath}")
        
        if not enabled_patch_names:
            print(f"ERROR: No patches found in {filepath}")
            sys.exit(1)
            
        return enabled_patch_names
    except FileNotFoundError:
        print(f"ERROR: {filepath} not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


def fetch_patches_data(url="https://raw.githubusercontent.com/inotia00/revanced-patches/revanced-extended/patches.json"):
    try:
        print(f"Fetching patches data from {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch patches data: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in patches data: {e}")
        sys.exit(1)


def find_compatible_version(patches_data, enabled_patches, target_package="com.google.android.apps.youtube.music"):
    version_support = defaultdict(int)
    patch_details = {}
    supports_all_versions = True
    
    print(f"\nSearching for compatible versions of {target_package}...")
    
    for patch in patches_data:
        patch_name = patch.get("name")
        if patch_name in enabled_patches:
            compat_packages = patch.get("compatiblePackages", {})
            
            # Handle both list and dict formats for compatiblePackages
            if isinstance(compat_packages, dict):
                # New format: {"package.name": ["version1", "version2"]}
                versions = compat_packages.get(target_package, [])
                if versions:
                    print(f"  - {patch_name}: supports versions {versions}")
                    patch_details[patch_name] = versions
                    supports_all_versions = False
                    for version in versions:
                        version_support[version] += 1
                elif target_package in compat_packages:
                    print(f"  - {patch_name}: supports all versions")
            else:
                # Old format: list of dicts or strings
                for compat_package in compat_packages:
                    if isinstance(compat_package, str):
                        package_name = compat_package
                        versions = []
                    elif isinstance(compat_package, dict):
                        package_name = compat_package.get("name")
                        versions = compat_package.get("versions", [])
                    else:
                        continue
                    
                    if package_name == target_package:
                        if versions:
                            print(f"  - {patch_name}: supports versions {versions}")
                            patch_details[patch_name] = versions
                            supports_all_versions = False
                            for version in versions:
                                version_support[version] += 1
                        else:
                            print(f"  - {patch_name}: supports all versions")
    
    # If all patches support all versions, no need to check compatibility
    if supports_all_versions:
        print("\n✓ All enabled patches support all versions. Will use latest APK.")
        return None
    
    if not version_support:
        print("\nERROR: No version information found for any enabled patches")
        sys.exit(1)
    
    # Find version that supports all patches (or most patches if no perfect match)
    required_count = len([p for p in enabled_patches if p in patch_details])
    
    if required_count == 0:
        print("\nERROR: None of the enabled patches have version constraints")
        sys.exit(1)
    
    # Sort versions by support count (descending) and then by version string (descending)
    sorted_versions = sorted(
        version_support.items(),
        key=lambda x: (x[1], x[0]),
        reverse=True
    )
    
    print(f"\nRequired patches with version constraints: {required_count}")
    print(f"Top compatible versions:")
    for version, count in sorted_versions[:5]:
        percentage = (count / required_count) * 100
        print(f"  - {version}: {count}/{required_count} patches ({percentage:.1f}%)")
    
    # Get the best match
    compatible_version, support_count = sorted_versions[0]
    
    if support_count < required_count:
        print(f"\nWARNING: No version supports all patches. Using {compatible_version} which supports {support_count}/{required_count} patches")
    else:
        print(f"\n✓ Compatible version found: {compatible_version}")
    
    return compatible_version


def save_outputs(version, enabled_patches):
    # Write to GitHub environment
    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a') as f:
            if version is None:
                f.write(f"YT_MUSIC_USE_LATEST=true\n")
                print(f"\n✓ Set YT_MUSIC_USE_LATEST=true for latest version download")
            else:
                f.write(f"YT_MUSIC_VERSION={version}\n")
                f.write(f"YT_MUSIC_USE_LATEST=false\n")
                print(f"\n✓ Saved YT_MUSIC_VERSION={version} to GitHub environment")
    else:
        if version is None:
            print(f"\nYT_MUSIC_USE_LATEST=true")
        else:
            print(f"\nYT_MUSIC_VERSION={version}")

def main():    
    # Load enabled patches
    enabled_patches = load_enabled_patches()
    
    # Fetch patches data
    patches_data = fetch_patches_data()
    
    # Find compatible version
    compatible_version = find_compatible_version(patches_data, enabled_patches)
    
    # Save outputs
    save_outputs(compatible_version, enabled_patches)
    # Save patches list for later use
    
    with open('enabled_patches.txt', 'w') as f:
        for patch in enabled_patches:
            f.write(f"{patch}\n")

if __name__ == "__main__":
    main()