"""
Comprehensive tests for cryptographic modules
=============================================

Tests for KeyManager, MerkleLog, and ProductionCryptoProvider.
"""

import pytest
import hashlib
import secrets
from crypto.amcis_key_manager import KeyManager
from crypto.amcis_merkle_log import MerkleLog
from crypto.amcis_hybrid_pqc import ProductionCryptoProvider


class TestKeyManager:
    """Test cases for KeyManager"""
    
    def test_initialization(self):
        """Test KeyManager initialization"""
        km = KeyManager()
        assert km is not None
    
    def test_generate_symmetric_key(self):
        """Test symmetric key generation"""
        km = KeyManager()
        key = km.generate_symmetric_key(algorithm="AES-256-GCM")
        assert key is not None
        assert len(key) > 0
    
    def test_generate_asymmetric_keypair(self):
        """Test asymmetric key pair generation with production crypto"""
        km = KeyManager()
        # Updated to use production crypto provider
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        assert keypair.kem_private_bytes is not None
        assert keypair.kem_public_bytes is not None
        assert len(keypair.kem_public_bytes) == 32  # X25519
    
    def test_key_rotation(self):
        """Test key rotation functionality"""
        km = KeyManager()
        key_id = "test-key-001"
        old_key = km.generate_symmetric_key()
        km.store_key(key_id, old_key)
        
        # Rotate key
        new_key = km.rotate_key(key_id)
        assert new_key is not None
        assert new_key != old_key
    
    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        km = KeyManager()
        plaintext = b"Test message for encryption"
        
        key = km.generate_symmetric_key()
        ciphertext = km.encrypt(plaintext, key)
        decrypted = km.decrypt(ciphertext, key)
        
        assert decrypted == plaintext
    
    def test_invalid_key_handling(self):
        """Test handling of invalid keys"""
        km = KeyManager()
        
        with pytest.raises(Exception):
            km.encrypt(b"test", b"invalid-key")


class TestMerkleLog:
    """Test cases for MerkleLog"""
    
    def test_initialization(self):
        """Test MerkleLog initialization"""
        log = MerkleLog()
        assert log is not None
    
    def test_append_entry(self):
        """Test appending entries to log"""
        log = MerkleLog()
        entry = {"event": "test", "timestamp": "2026-03-15T12:00:00Z"}
        
        index = log.append(entry)
        assert index == 0
        
        index2 = log.append(entry)
        assert index2 == 1
    
    def test_integrity_verification(self):
        """Test log integrity verification"""
        log = MerkleLog()
        
        # Add entries
        for i in range(10):
            log.append({"event": f"test-{i}"})
        
        # Verify integrity
        assert log.verify_integrity() == True
    
    def test_proof_generation(self):
        """Test generation of inclusion proofs"""
        log = MerkleLog()
        
        entries = [{"event": f"test-{i}"} for i in range(5)]
        for entry in entries:
            log.append(entry)
        
        proof = log.get_proof(2)
        assert proof is not None
        
        # Verify proof
        assert log.verify_proof(2, entries[2], proof) == True


class TestProductionCrypto:
    """Test production cryptography implementation"""
    
    def test_provider_initialization(self):
        """Test provider initializes correctly"""
        provider = ProductionCryptoProvider()
        info = provider.get_info()
        
        assert info["status"] == "PRODUCTION"
        assert "X25519" in info["kem"]
    
    def test_keypair_generation(self):
        """Test keypair generation"""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        assert keypair.kem_public_bytes is not None
        assert len(keypair.kem_public_bytes) == 32
    
    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        plaintext = b"Test message"
        ciphertext = provider.encrypt(plaintext, keypair.kem_public_bytes)
        decrypted = provider.decrypt(ciphertext, keypair)
        
        assert decrypted == plaintext
    
    def test_sign_verify(self):
        """Test signing and verification"""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        message = b"Test message"
        signature = provider.sign(message, keypair)
        
        assert provider.verify(message, signature, keypair.sig_public_bytes) is True
    
    def test_verify_wrong_message(self):
        """Test verification fails with wrong message"""
        provider = ProductionCryptoProvider()
        keypair = provider.generate_keypair()
        
        signature = provider.sign(b"Original", keypair)
        assert provider.verify(b"Different", signature, keypair.sig_public_bytes) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
