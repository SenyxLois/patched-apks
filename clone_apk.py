#!/usr/bin/env python3
"""
clone_apk.py - Change package name of an APK using APKEditor

Decodes the APK with APKEditor (keeping DEX intact with -dex), modifies the
package name and authorities in AndroidManifest.xml and public.xml, then
rebuilds the APK.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

# Ensure UTF-8 stdout on all platforms
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


def run_cmd(cmd, description):
    print(f"[clone_apk] {description}...")
    print(f"[clone_apk] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode != 0:
        print(f"[clone_apk] ERROR: {description} failed (exit code {result.returncode}):")
        print(result.stdout)
        sys.exit(result.returncode)
    else:
        # Print summary or last few lines
        lines = result.stdout.strip().splitlines()
        for line in lines[-5:]:
            print(f"  {line}")


def modify_manifest(manifest_path, old_pkg, new_pkg):
    print(f"[clone_apk] Modifying {manifest_path}...")
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update manifest package attribute (supports both ' and " quotes)
    content = re.sub(
        r'package=([\'"])' + re.escape(old_pkg) + r'\1',
        f'package="{new_pkg}"',
        content,
        count=1
    )

    # 2. Update provider authorities
    def replace_authorities(m):
        return m.group(0).replace(old_pkg, new_pkg)
    content = re.sub(r'android:authorities=([\'"])[^\'"]*\1', replace_authorities, content)

    # 3. Update custom permission declarations and uses-permissions
    def replace_permissions(m):
        return m.group(0).replace(old_pkg, new_pkg)
    content = re.sub(r'(<(?:uses-)?permission[^>]*android:name=([\'"]))[^\'"]*(\2)', replace_permissions, content)

    # 4. Update custom broadcast action names
    content = re.sub(r'(<action[^>]*android:name=([\'"]))' + re.escape(old_pkg), r'\1' + new_pkg, content)

    # 5. Fix any relative class names (e.g. android:name=".SomeActivity") so Android
    # does not prepend the new package name when resolving classes in DEX.
    def expand_relative_class(m):
        attr = m.group(1)
        val = m.group(2)
        if val.startswith('.'):
            return f'{attr}"{old_pkg}{val}"'
        return m.group(0)

    content = re.sub(r'(android:(?:name|backupAgent|targetActivity)=)"([^"]+)"', expand_relative_class, content)

    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[clone_apk] Successfully updated {manifest_path}")


def modify_resources(work_dir, old_pkg, new_pkg):
    # Find all public.xml and strings.xml in resources
    resources_dir = os.path.join(work_dir, 'resources')
    if not os.path.isdir(resources_dir):
        print(f"[clone_apk] No resources dir found at {resources_dir}, skipping resource updates")
        return

    for root, _, files in os.walk(resources_dir):
        for fname in files:
            if fname == 'public.xml':
                pub_file = os.path.join(root, fname)
                with open(pub_file, 'r', encoding='utf-8', errors='ignore') as f:
                    pub_content = f.read()
                if f'package="{old_pkg}"' in pub_content:
                    pub_content = pub_content.replace(f'package="{old_pkg}"', f'package="{new_pkg}"')
                    with open(pub_file, 'w', encoding='utf-8') as f:
                        f.write(pub_content)
                    print(f"[clone_apk] Updated package attribute in {pub_file}")


def main():
    parser = argparse.ArgumentParser(description="Clone APK by modifying package name using APKEditor.")
    parser.add_argument("--input", "-i", required=True, help="Input APK file path")
    parser.add_argument("--output", "-o", required=True, help="Output unsigned APK file path")
    parser.add_argument("--old-pkg", required=True, help="Original package name (e.g. com.google.android.apps.youtube.music)")
    parser.add_argument("--new-pkg", required=True, help="New clone package name (e.g. com.senyx.android.apps.youtube.music)")
    parser.add_argument("--apk-editor", default="apk-editor.jar", help="Path to APKEditor jar (default: apk-editor.jar)")
    parser.add_argument("--work-dir", default="tmp_clone_work", help="Temporary directory for decoding")
    parser.add_argument("--java-bin", default="java", help="Java executable name or path")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[clone_apk] ERROR: Input APK not found: {args.input}")
        sys.exit(1)

    if not os.path.isfile(args.apk_editor):
        print(f"[clone_apk] ERROR: APKEditor jar not found: {args.apk_editor}")
        sys.exit(1)

    # Clean working dir if exists
    if os.path.exists(args.work_dir):
        shutil.rmtree(args.work_dir)

    # Step 1: Decode with APKEditor
    decode_cmd = [
        args.java_bin, "-jar", args.apk_editor,
        "d", "-dex", "-t", "xml",
        "-i", args.input,
        "-o", args.work_dir
    ]
    run_cmd(decode_cmd, f"Decoding {args.input} with APKEditor")

    manifest_file = os.path.join(args.work_dir, "AndroidManifest.xml")
    if not os.path.isfile(manifest_file):
        print(f"[clone_apk] ERROR: AndroidManifest.xml not found in {args.work_dir}")
        sys.exit(1)

    # Step 2: Modify AndroidManifest.xml
    modify_manifest(manifest_file, args.old_pkg, args.new_pkg)

    # Step 3: Modify resources (public.xml)
    modify_resources(args.work_dir, args.old_pkg, args.new_pkg)

    # Step 4: Build APK with APKEditor
    build_cmd = [
        args.java_bin, "-jar", args.apk_editor,
        "b",
        "-i", args.work_dir,
        "-o", args.output
    ]
    run_cmd(build_cmd, f"Rebuilding clone APK to {args.output}")

    # Step 5: Clean up working directory
    shutil.rmtree(args.work_dir, ignore_errors=True)

    if not os.path.isfile(args.output):
        print(f"[clone_apk] ERROR: Output APK was not created: {args.output}")
        sys.exit(1)

    output_size = os.path.getsize(args.output)
    print(f"[clone_apk] SUCCESS: Built clone APK {args.output} ({output_size:,} bytes) with package {args.new_pkg}")


if __name__ == "__main__":
    main()
