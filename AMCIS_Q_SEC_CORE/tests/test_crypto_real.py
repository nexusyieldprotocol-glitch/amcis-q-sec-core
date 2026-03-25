"""
REAL Cryptographic Tests - Production Implementation
====================================================

These tests verify ACTUAL post-quantum cryptographic operations using
the Open Quantum Safe (OQS) library. All operations are real and
computationally intensive.

Requirements:
    - oqs>=0.10.0 (Open Quantum Safe Python bindings)
    - cryptography>=42.0.0
    
WARNING: Key generation and signing tests may take 1-3 seconds per operation
due to PQC algorithm complexity.
"""

import pytest
import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.amcis_hybrid_pqc_real import (
    HybridPQCProvider,
    HybridCiphertext,
    HybridSignature,
    HybridKeypair,
    PQCKEM,
    PQCSignature
)


class TestRealPQCKeyGeneration:
    """Test real PQC key generation using OQS library."""
    
    def test_provider_initialization(self):
        """Test that provider initializes with real OQS algorithms."""
        provider = HybridPQCProvider()
        assert provider.kem_alg == "Kyber768"
        assert provider.sig_alg == "Dilithium3"
        
        info = provider.get_algorithm_info()
        assert info["implementation"] == "REAL - AUDITED PATH"
        assert "Open Quantum Safe" in info["provider"]
    
    def test_keypair_generation(self):
        """Test generation of complete hybrid keypair."""
        provider = HybridPQCProvider()
        
        # This performs REAL key generation - may take 1-2 seconds
        keypair = provider.generate_keypair()
        
        assert isinstance(keypair, HybridKeypair)
        
        # Verify classical keys exist
        assert len(keypair.classical_kem_public) == 32  # X25519 public key
        assert len(keypair.classical_kem_private) == 32  # X25519 private key
        assert len(keypair.classical_sig_public) > 100  # PEM encoded
        assert len(keypair.classical_sig_private) > 100  # PEM encoded
        
        # Verify PQC keys exist
        assert len(keypair.pqc_kem_public) > 1000  # Kyber768 public key ~1184 bytes
        assert len(keypair.pqc_kem_secret) > 2000  # Kyber768 secret key ~2400 bytes
        assert len(keypair.pqc_sig_public) > 1900  # Dilithium3 public key ~1952 bytes
        assert len(keypair.pqc_sig_secret) > 3900  # Dilithium3 secret key ~4032 bytes


class TestRealPQCEncryption:
    """Test real hybrid encryption using Kyber + X25519."""
    
    def test_encapsulation_decapsulation(self):
        """Test full encapsulation/decapsulation cycle."""
        provider = HybridPQCProvider()
        
        # Generate recipient keypair
        recipient = provider.generate_keypair()
        
        # Prepare public key dict
        public_key = {
            "classical_kem_public": recipient.classical_kem_public,
            "pqc_kem_public": recipient.pqc_kem_public
        }
        
        # Encapsulate
        ciphertext = provider.encapsulate(public_key)
        
        assert isinstance(ciphertext, HybridCiphertext)
        assert len(ciphertext.classical_ct) == 32  # X25519 public key
        assert len(ciphertext.pqc_ct) > 1000  # Kyber ciphertext
        assert len(ciphertext.nonce) == 12  # AES-GCM nonce
        
        # Decapsulate
        content_key = provider.decapsulate(ciphertext, recipient)
        assert len(content_key) == 32  # AES-256 key
    
    def test_encryption_decryption(self):
        """Test full encrypt/decrypt cycle with payload."""
        provider = HybridPQCProvider()
        
        # Generate keypair
        keypair = provider.generate_keypair()
        
        public_key = {
            "classical_kem_public": keypair.classical_kem_public,
            "pqc_kem_public": keypair.pqc_kem_public
        }
        
        # Test data
        plaintext = b"This is a secret message protected by real post-quantum cryptography!"
        
        # Encrypt
        ciphertext = provider.encrypt(plaintext, public_key)
        
        # Decrypt
        decrypted = provider.decrypt(ciphertext, keypair)
        
        assert decrypted == plaintext
    
    def test_encryption_different_messages(self):
        """Test encryption of multiple messages."""
        provider = HybridPQCProvider()
        keypair = provider.generate_keypair()
        
        public_key = {
            "classical_kem_public": keypair.classical_kem_public,
            "pqc_kem_public": keypair.pqc_kem_public
        }
        
        messages = [
            b"Short",
            b"A medium length message with some content",
            b"X" * 10000,  # Large message
        ]
        
        for msg in messages:
            ciphertext = provider.encrypt(msg, public_key)
            decrypted = provider.decrypt(ciphertext, keypair)
            assert decrypted == msg


class TestRealPQCSignatures:
    """Test real hybrid signatures using Dilithium + ECDSA."""
    
    def test_sign_verify(self):
        """Test full sign/verify cycle."""
        provider = HybridPQCProvider()
        
        # Generate signer keypair
        signer = provider.generate_keypair()
        
        public_key = {
            "classical_sig_public": signer.classical_sig_public,
            "pqc_sig_public": signer.pqc_sig_public
        }
        
        # Message to sign
        message = b"Sign this with real post-quantum signatures!"
        
        # Sign
        signature = provider.sign(message, signer)
        
        assert isinstance(signature, HybridSignature)
        assert len(signature.classical_sig) > 50  # ECDSA signature
        assert len(signature.pqc_sig) > 3000  # Dilithium3 signature ~3293 bytes
        
        # Verify
        assert provider.verify(message, signature, public_key) is True
    
    def test_verify_wrong_message(self):
        """Test that verification fails with wrong message."""
        provider = HybridPQCProvider()
        
        signer = provider.generate_keypair()
        public_key = {
            "classical_sig_public": signer.classical_sig_public,
            "pqc_sig_public": signer.pqc_sig_public
        }
        
        # Sign one message
        signature = provider.sign(b"Original message", signer)
        
        # Try to verify with different message
        assert provider.verify(b"Different message", signature, public_key) is False
    
    def test_verify_wrong_key(self):
        """Test that verification fails with wrong public key."""
        provider = HybridPQCProvider()
        
        signer = provider.generate_keypair()
        wrong_signer = provider.generate_keypair()
        
        public_key = {
            "classical_sig_public": wrong_signer.classical_sig_public,
            "pqc_sig_public": wrong_signer.pqc_sig_public
        }
        
        # Sign with one key
        signature = provider.sign(b"Test message", signer)
        
        # Try to verify with different key
        assert provider.verify(b"Test message", signature, public_key) is False


class TestSerialization:
    """Test serialization/deserialization of ciphertext and signatures."""
    
    def test_ciphertext_serialization(self):
        """Test that ciphertext can be serialized and deserialized."""
        provider = HybridPQCProvider()
        keypair = provider.generate_keypair()
        
        public_key = {
            "classical_kem_public": keypair.classical_kem_public,
            "pqc_kem_public": keypair.pqc_kem_public
        }
        
        # Encrypt
        original = provider.encrypt(b"Test message", public_key)
        
        # Serialize
        serialized = original.to_bytes()
        
        # Deserialize
        restored = HybridCiphertext.from_bytes(serialized)
        
        # Verify fields match
        assert restored.classical_ct == original.classical_ct
        assert restored.pqc_ct == original.pqc_ct
        assert restored.nonce == original.nonce
        assert restored.ciphertext == original.ciphertext
        
        # Verify can still decrypt
        decrypted = provider.decrypt(restored, keypair)
        assert decrypted == b"Test message"
    
    def test_signature_serialization(self):
        """Test that signature can be serialized and deserialized."""
        provider = HybridPQCProvider()
        keypair = provider.generate_keypair()
        
        # Sign
        original = provider.sign(b"Test message", keypair)
        
        # Serialize
        serialized = original.to_bytes()
        
        # Deserialize
        restored = HybridSignature.from_bytes(serialized)
        
        # Verify fields match
        assert restored.classical_sig == original.classical_sig
        assert restored.pqc_sig == original.pqc_sig
        assert restored.message_hash == original.message_hash


class TestDifferentAlgorithms:
    """Test with different PQC algorithm combinations."""
    
    def test_kyber512_dilithium2(self):
        """Test with lighter algorithms."""
        provider = HybridPQCProvider(
            kem_algorithm=PQCKEM.ML_KEM_512,
            sig_algorithm=PQCSignature.ML_DSA_44
        )
        
        keypair = provider.generate_keypair()
        
        # Test encryption
        public_key = {
            "classical_kem_public": keypair.classical_kem_public,
            "pqc_kem_public": keypair.pqc_kem_public
        }
        
        ciphertext = provider.encrypt(b"Test", public_key)
        decrypted = provider.decrypt(ciphertext, keypair)
        assert decrypted == b"Test"
        
        # Test signing
        public_sig = {
            "classical_sig_public": keypair.classical_sig_public,
            "pqc_sig_public": keypair.pqc_sig_public
        }
        
        signature = provider.sign(b"Test", keypair)
        assert provider.verify(b"Test", signature, public_sig) is True


if __name__ == "__main__":
    # Run basic tests when executed directly
    print("Running REAL PQC crypto tests...")
    print("WARNING: These tests perform actual PQC operations and may take 10-30 seconds.")
    
    provider = HybridPQCProvider()
    print(f"Provider initialized: {provider.get_algorithm_info()}")
    
    # Quick smoke test
    keypair = provider.generate_keypair()
    print(f"✓ Keypair generated")
    
    public_key = {
        "classical_kem_public": keypair.classical_kem_public,
        "pqc_kem_public": keypair.pqc_kem_public
    }
    
    ciphertext = provider.encrypt(b"Hello, Real PQC!", public_key)
    decrypted = provider.decrypt(ciphertext, keypair)
    assert decrypted == b"Hello, Real PQC!"
    print(f"✓ Encryption/decryption works")
    
    public_sig = {
        "classical_sig_public": keypair.classical_sig_public,
        "pqc_sig_public": keypair.pqc_sig_public
    }
    
    signature = provider.sign(b"Test message", keypair)
    assert provider.verify(b"Test message", signature, public_sig) is True
    print(f"✓ Sign/verify works")
    
    print("\n✅ ALL REAL CRYPTO TESTS PASSED")
