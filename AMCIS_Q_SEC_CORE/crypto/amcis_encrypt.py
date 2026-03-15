#!/usr/bin/env python3
"""
AMCIS Q-SEC CORE - File Encryption Module
Encrypts sensitive project files with AES-256-GCM
"""

import os
import sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

AMCIS_BASE = Path.home() / "AMCIS_Q_SEC_CORE"
VAULT_PATH = AMCIS_BASE / ".VAULT_MASTER"
KEY_PATH = VAULT_PATH / "keys" / "amcis_master.key"
IV_PATH = VAULT_PATH / "keys" / "amcis_master.iv"

def load_keys():
    """Load encryption keys from secure storage"""
    with open(KEY_PATH, 'r') as f:
        key = bytes.fromhex(f.read().strip())
    with open(IV_PATH, 'r') as f:
        iv = bytes.fromhex(f.read().strip())
    return key, iv

def encrypt_file(file_path: Path, output_path: Path = None):
    """Encrypt a single file using AES-256-GCM"""
    key, iv = load_keys()
    
    with open(file_path, 'rb') as f:
        plaintext = f.read()
    
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=default_backend()
    ).encryptor()
    
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    
    if not output_path:
        output_path = Path(str(file_path) + '.encrypted')
    
    with open(output_path, 'wb') as f:
        f.write(iv + encryptor.tag + ciphertext)
    
    print(f"[+] Encrypted: {file_path} -> {output_path}")
    return output_path

def decrypt_file(file_path: Path, output_path: Path = None):
    """Decrypt a file encrypted with AES-256-GCM"""
    key, _ = load_keys()
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    iv = data[:16]
    tag = data[16:32]
    ciphertext = data[32:]
    
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(iv, tag),
        backend=default_backend()
    ).decryptor()
    
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    if not output_path:
        output_path = Path(str(file_path).replace('.encrypted', '.decrypted'))
    
    with open(output_path, 'wb') as f:
        f.write(plaintext)
    
    print(f"[+] Decrypted: {file_path} -> {output_path}")
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AMCIS File Encryption")
    parser.add_argument("action", choices=["encrypt", "decrypt"])
    parser.add_argument("file", help="File to process")
    parser.add_argument("-o", "--output", help="Output file path")
    args = parser.parse_args()
    
    file_path = Path(args.file)
    output_path = Path(args.output) if args.output else None
    
    if args.action == "encrypt":
        encrypt_file(file_path, output_path)
    else:
        decrypt_file(file_path, output_path)
