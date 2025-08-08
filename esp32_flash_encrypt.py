#!/usr/bin/env python3
"""
ESP32 Flash Encryption Automation Script
Automates the process of setting up flash encryption on ESP32
"""

import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path


def fix_command_for_windows(cmd):
    """Fix command for Windows by adding python prefix to .py files"""
    if platform.system() == "Windows" and len(cmd) > 0:
        if cmd[0].endswith(".py"):
            return ["python"] + cmd
    return cmd


def run_command(cmd, description=""):
    """Run a command and handle errors"""
    # Fix command for Windows
    cmd = fix_command_for_windows(cmd)

    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warning: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: Command not found. Make sure ESP-IDF tools are in PATH")
        return False


def check_file_exists(filepath, description=""):
    """Check if a file exists and print status"""
    if os.path.exists(filepath):
        print(f"✓ Found: {description} ({filepath})")
        return True
    else:
        print(f"✗ Missing: {description} ({filepath})")
        return False


def main():
    parser = argparse.ArgumentParser(description="ESP32 Flash Encryption Setup")
    parser.add_argument(
        "--port", required=True, help="Serial port (e.g., COM18 or /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--chip", default="esp32", help="ESP chip type (default: esp32)"
    )
    parser.add_argument(
        "--key-file",
        default="my_flash_encryption_key.bin",
        help="Flash encryption key filename",
    )
    parser.add_argument(
        "--build-dir", default=".pio/build/esp32dev", help="PlatformIO build directory"
    )
    parser.add_argument(
        "--development",
        action="store_true",
        help="Use development mode (FLASH_CRYPT_CNT=1)",
    )
    parser.add_argument(
        "--skip-efuse",
        action="store_true",
        help="Skip eFuse burning (useful for testing)",
    )
    parser.add_argument(
        "--encrypt-only", action="store_true", help="Only encrypt files, skip flashing"
    )
    parser.add_argument(
        "--flash-only",
        action="store_true",
        help="Only flash (assume files already encrypted)",
    )

    args = parser.parse_args()

    # Convert paths to Path objects
    build_dir = Path(args.build_dir)
    key_file = Path(args.key_file)

    print("ESP32 Flash Encryption Setup Script")
    print("====================================")
    print(f"Port: {args.port}")
    print(f"Chip: {args.chip}")
    print(f"Key file: {key_file}")
    print(f"Build directory: {build_dir}")
    print(f"Mode: {'Development' if args.development else 'Production'}")

    # Check if build directory exists
    if not build_dir.exists():
        print(f"\nError: Build directory {build_dir} does not exist.")
        print("Run 'pio run' first to build your project.")
        sys.exit(1)

    # Define file paths
    bootloader_bin = build_dir / "bootloader.bin"
    partitions_bin = build_dir / "partitions.bin"
    firmware_bin = build_dir / "firmware.bin"

    encrypted_bootloader = "encrypted_bootloader.bin"
    encrypted_partitions = "encrypted_partitions.bin"
    encrypted_firmware = "encrypted_firmware.bin"

    if not args.flash_only:
        # Step 1: Generate Flash Encryption Key
        if not key_file.exists():
            print("\nStep 1: Generating Flash Encryption Key")
            if not run_command(
                ["espsecure.py", "generate_flash_encryption_key", str(key_file)],
                "Generate flash encryption key",
            ):
                sys.exit(1)
        else:
            print(f"\nStep 1: Using existing key file: {key_file}")

        # Check source files exist
        print("\nChecking source files...")
        files_exist = True
        files_exist &= check_file_exists(bootloader_bin, "Bootloader")
        files_exist &= check_file_exists(partitions_bin, "Partition table")
        files_exist &= check_file_exists(firmware_bin, "Firmware")

        if not files_exist:
            print("\nError: Required build files are missing. Run 'pio run' first.")
            sys.exit(1)

    if not args.skip_efuse and not args.encrypt_only and not args.flash_only:
        # Step 2: Burn the Flash Encryption Key into eFuse
        print("\nStep 2: Burning Flash Encryption Key into eFuse")
        if not run_command(
            [
                "espefuse.py",
                "--port",
                args.port,
                "burn_key",
                "flash_encryption",
                str(key_file),
            ],
            "Burn flash encryption key",
        ):
            print("Failed to burn encryption key. Continuing anyway...")

        # Step 3: Burn the FLASH_CRYPT_CNT and FLASH_CRYPT_CONFIG eFuses
        print("\nStep 3: Burning FLASH_CRYPT_CNT and FLASH_CRYPT_CONFIG eFuses")

        # Set FLASH_CRYPT_CNT based on mode
        crypt_cnt = "1" if args.development else "127"

        if not run_command(
            [
                "espefuse.py",
                "--port",
                args.port,
                "--chip",
                args.chip,
                "burn_efuse",
                "FLASH_CRYPT_CNT",
                crypt_cnt,
            ],
            f"Burn FLASH_CRYPT_CNT to {crypt_cnt}",
        ):
            print("Failed to burn FLASH_CRYPT_CNT. Continuing anyway...")

        if not run_command(
            [
                "espefuse.py",
                "--port",
                args.port,
                "--chip",
                args.chip,
                "burn_efuse",
                "FLASH_CRYPT_CONFIG",
                "0xF",
            ],
            "Burn FLASH_CRYPT_CONFIG to 0xF",
        ):
            print("Failed to burn FLASH_CRYPT_CONFIG. Continuing anyway...")

        # Step 4: Burn Additional Security eFuses (Production only)
        if not args.development:
            print("\nStep 4: Burning Additional Security eFuses (Production)")
            security_efuses = [
                ("DISABLE_DL_ENCRYPT", "0x1"),
                ("DISABLE_DL_DECRYPT", "0x1"),
                ("DISABLE_DL_CACHE", "0x1"),
                ("JTAG_DISABLE", "0x1"),
            ]

            for efuse_name, efuse_value in security_efuses:
                run_command(
                    [
                        "espefuse.py",
                        "--port",
                        args.port,
                        "burn_efuse",
                        efuse_name,
                        efuse_value,
                    ],
                    f"Burn {efuse_name}",
                )

            # Step 5: Write Protect Security eFuses
            print("\nStep 5: Write Protecting Security eFuses")
            run_command(
                [
                    "espefuse.py",
                    "--port",
                    args.port,
                    "write_protect_efuse",
                    "DIS_CACHE",
                ],
                "Write protect DIS_CACHE",
            )

    if not args.flash_only:
        # Step 6-8: Encrypt all binaries
        encryption_tasks = [
            (bootloader_bin, encrypted_bootloader, "0x1000", "Encrypt bootloader"),
            (partitions_bin, encrypted_partitions, "0x8000", "Encrypt partition table"),
            (firmware_bin, encrypted_firmware, "0x10000", "Encrypt firmware"),
        ]

        for source_file, output_file, address, description in encryption_tasks:
            print(f"\n{description}")
            if not run_command(
                [
                    "espsecure.py",
                    "encrypt_flash_data",
                    "--keyfile",
                    str(key_file),
                    "--address",
                    address,
                    "--output",
                    output_file,
                    str(source_file),
                ],
                description,
            ):
                print(f"Failed to encrypt {source_file}")
                sys.exit(1)

    if not args.encrypt_only:
        # Step 9: Flash all encrypted binaries
        print("\nStep 9: Flashing Encrypted Firmware")

        # Check encrypted files exist
        encrypted_files = [
            encrypted_bootloader,
            encrypted_partitions,
            encrypted_firmware,
        ]
        for f in encrypted_files:
            if not os.path.exists(f):
                print(f"Error: Encrypted file {f} not found!")
                sys.exit(1)

        flash_cmd = [
            "esptool.py",
            "--chip",
            args.chip,
            "--port",
            args.port,
            "write_flash",
            "0x1000",
            encrypted_bootloader,
            "0x8000",
            encrypted_partitions,
            "0x10000",
            encrypted_firmware,
        ]

        if not run_command(flash_cmd, "Flash all encrypted binaries"):
            print("Failed to flash encrypted firmware!")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS: ESP32 Flash Encryption Setup Complete!")
    print("=" * 60)

    if args.development:
        print("\nNOTE: Development mode is enabled. This allows re-flashing.")
        print("For production, use --development flag to disable development mode.")
    else:
        print("\nNOTE: Production mode enabled. Re-flashing will require")
        print("special procedures or may be permanently disabled.")

    print(f"\nEncrypted files generated:")
    print(f"  - {encrypted_bootloader}")
    print(f"  - {encrypted_partitions}")
    print(f"  - {encrypted_firmware}")

    # Cleanup option
    cleanup = input("\nDelete encrypted files? (y/N): ").strip().lower()
    if cleanup == "y":
        for f in [encrypted_bootloader, encrypted_partitions, encrypted_firmware]:
            if os.path.exists(f):
                os.remove(f)
                print(f"Deleted {f}")


if __name__ == "__main__":
    main()
