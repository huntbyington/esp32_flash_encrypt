# ESP32 Flash Encryption Automation Script

![ESP32 Security](https://img.shields.io/badge/ESP32-Security-critical)
![Python](https://img.shields.io/badge/Python-3.7%2B-blue)

Automates the process of setting up flash encryption on ESP32 devices using PlatformIO. This script handles key generation, eFuse burning, binary encryption, and flashing in a single workflow.

## ⚠️ Critical Security Warning

**This script performs irreversible hardware operations:**
- Burns encryption keys into eFuses (cannot be changed later)
- Sets FLASH_CRYPT_CNT (permanently enables encryption)
- Write-protects security eFuses
- **Improper use may permanently brick your device!**

## Features
- 🔑 Generates secure flash encryption keys
- 🔥 Burns encryption keys and security eFuses
- 🔒 Encrypts bootloader, partitions, and firmware
- ⚡ Flashes encrypted binaries to device
- ⚙️ Supports both development and production modes
- ✅ PlatformIO project integration

## Prerequisites
1. **Hardware**:
   - ESP32 development board
   - USB serial connection

2. **Software**:
   - Python 3.7+
   - PlatformIO CLI
   - ESP-IDF tools (`esptool.py`, `espsecure.py`, `espefuse.py`)
     ```bash
     pip install esptool
     ```

## Installation
```bash
# Download the script
curl -O https://raw.githubusercontent.com/yourusername/esp32-encryption/main/esp32_encrypt.py
chmod +x esp32_encrypt.py

**Acknowledgement**  
*This README documentation was generated with the assistance of a Large Language Model (LLM).
