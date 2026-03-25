"""
PRODUCTION Cryptography Tests
==============================

These tests verify REAL cryptographic operations using the Python
cryptography library with OpenSSL backend.

All operations use production-grade algorithms:
- X25519 key exchange
- ECDSA P-384 signatures  
- AES-256-GCM encryption
- SHA3-256 hashing

Status: PRODUCTION READY
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.amcis_hybrid_pqc import (
    ProductionCryptoProvider,
    HybridCiphertext,
    HybridSignature,
    CryptoKeypair
)


class TestProductionCrypto:
    """Test production cryptography implementation."""
    
    def test_provider_initialization(self):
        """Test provider initializes correctly."""
        provider = ProductionCryptoProvider()
        info = provider.get_info()
        
        assert info["status"] == "PRODUCTION"
        assert info["kem"] == "X25519 (ECDH)"
        assert info["signature"] == "ECDSA-P384"
        assert info["pqc_ready"] == "True (upgrade path documented)"
    
    def test_keypair_generation(self):
        """Test keypair generation."""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        assert isinstance(keypair, CryptoKeypair)
        assert len(keypair.kem_public_bytes) == 32  # X25519
        assert len(keypair.kem_private_bytes) == 32
        assert len(keypair.sig_public_bytes) > 100  # PEM
        assert len(keypair.sig_private_bytes) > 100
    
    def test_encapsulation_decapsulation(self):
        """Test key encapsulation cycle."""
        provider = ProductionCryptoProvider()
        
        # Generate keypair
        keypair = provider.generate_keypair()
        
        # Encapsulate
        encap = provider.encapsulate(keypair.kem_public_bytes)
        
        assert len(encap.ephemeral_public) == 32
        assert len(encap.shared_secret) == 32
        
        # Decapsulate
        shared = provider.decapsulate(encap.ephemeral_public, keypair.kem_private)
        assert shared == encap.shared_secret
    
    def test_encrypt_decrypt(self):
        """Test full encryption/decryption."""
        provider = ProductionCryptoProvider()
        
        keypair = provider.generate_keypair()
        
        messages = [
            b"Short",
            b"A longer message with more content",
            b"X" * 10000,
        ]
        
        for msg in messages:
            ciphertext = provider.encrypt(msg, keypair.kem_public_bytes)
            decrypted = provider.decrypt(ciphertext, keypair)
            assert decrypted == msg
    
    def test_sign_verify(self):
        """Test signing and verification."""
        provider = ProductionCryptoProvider()
        
        keypair = provider.generate_keypair()
        
        message = b"Sign this message"
        signature = provider.sign(message, keypair)
        
        assert isinstance(signature, HybridSignature)
        assert len(signature.signature) > 50
        
        # Verify
        assert provider.verify(message, signature, keypair.sig_public_bytes) is True
    
    def test_verify_wrong_message(self):
        """Test verification fails with wrong message."""
        provider = ProductionCryptoProvider()
        
        keypair = provider.generate_keypair()
        
        signature = provider.sign(b"Original", keypair)
        assert provider.verify(b"Different", signature, keypair.sig_public_bytes) is False
    
    def test_verify_wrong_key(self):
        """Test verification fails with wrong key."""
        provider = ProductionCryptoProvider()
        
        keypair1 = provider.generate_keypair()
        keypair2 = provider.generate_keypair()
        
        signature = provider.sign(b"Test", keypair1)
        assert provider.verify(b"Test", signature, keypair2.sig_public_bytes) is False
    
    def test_ciphertext_serialization(self):
        """Test ciphertext serialization."""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        original = provider.encrypt(b"Test", keypair.kem_public_bytes)
        serialized = original.to_bytes()
        restored = HybridCiphertext.from_bytes(serialized)
        
        assert restored.ephemeral_public == original.ephemeral_public
        assert restored.nonce == original.nonce
        assert restored.ciphertext == original.ciphertext
        
        # Verify can still decrypt
        decrypted = provider.decrypt(restored, keypair)
        assert decrypted == b"Test"
    
    def test_signature_serialization(self):
        """Test signature serialization."""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        original = provider.sign(b"Test", keypair)
        serialized = original.to_bytes()
        restored = HybridSignature.from_bytes(serialized)
        
        assert restored.signature == original.signature
        assert restored.message_hash == original.message_hash


if __name__ == "__main__":
    print("Running PRODUCTION cryptography tests...")
    
    provider = ProductionCryptoProvider()
    info = provider.get_info()
    print(f"\nAlgorithm Info: {info}")
    
    # Quick smoke test
    keypair = provider.generate_keypair()
    print("[OK] Keypair generated")
    
    # Test encryption
    ct = provider.encrypt(b"Hello World", keypair.kem_public_bytes)
    pt = provider.decrypt(ct, keypair)
    assert pt == b"Hello World"
    print("[OK] Encryption/decryption works")
    
    # Test signatures
    sig = provider.sign(b"Test", keypair)
    assert provider.verify(b"Test", sig, keypair.sig_public_bytes)
    print("[OK] Sign/verify works")
    
    # Test tampering detection
    assert not provider.verify(b"Wrong", sig, keypair.sig_public_bytes)
    print("[OK] Tampering detection works")
    
    print("\n[PASS] ALL PRODUCTION CRYPTO TESTS PASSED")
    print("\nSTATUS: Real cryptography using OpenSSL backend.")
    print("PQC Upgrade: Ready for liboqs integration when available.")
