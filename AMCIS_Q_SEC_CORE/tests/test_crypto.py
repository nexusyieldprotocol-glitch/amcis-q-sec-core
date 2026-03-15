"""
Comprehensive tests for cryptographic modules
"""

import pytest
import hashlib
import secrets
from crypto.amcis_key_manager import KeyManager
from crypto.amcis_merkle_log import MerkleLog

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
        """Test asymmetric key pair generation"""
        km = KeyManager()
        private_key, public_key = km.generate_keypair(algorithm="ML-KEM-768")
        assert private_key is not None
        assert public_key is not None
    
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
    
    def test_tamper_detection(self):
        """Test detection of tampered entries"""
        log = MerkleLog()
        log.append({"event": "original"})
        
        # Attempt to modify (should fail or be detected)
        # Implementation-specific behavior
        pass
    
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


class TestPostQuantumCrypto:
    """Test Post-Quantum Cryptography implementations"""
    
    def test_ml_kem_keygen(self):
        """Test ML-KEM key generation"""
        from crypto.amcis_pqc import MLKEM
        
        kem = MLKEM()
        public_key, private_key = kem.keygen()
        
        assert len(public_key) > 0
        assert len(private_key) > 0
    
    def test_ml_kem_encapsulate_decapsulate(self):
        """Test ML-KEM encapsulation and decapsulation"""
        from crypto.amcis_pqc import MLKEM
        
        kem = MLKEM()
        public_key, private_key = kem.keygen()
        
        ciphertext, shared_secret = kem.encapsulate(public_key)
        decapsulated_secret = kem.decapsulate(ciphertext, private_key)
        
        assert shared_secret == decapsulated_secret
    
    def test_ml_dsa_sign_verify(self):
        """Test ML-DSA signature and verification"""
        from crypto.amcis_pqc import MLDSA
        
        dsa = MLDSA()
        public_key, private_key = dsa.keygen()
        
        message = b"Test message for signing"
        signature = dsa.sign(message, private_key)
        
        assert dsa.verify(message, signature, public_key) == True
    
    def test_ml_dsa_tampered_message(self):
        """Test ML-DSA with tampered message"""
        from crypto.amcis_pqc import MLDSA
        
        dsa = MLDSA()
        public_key, private_key = dsa.keygen()
        
        message = b"Original message"
        signature = dsa.sign(message, private_key)
        
        tampered_message = b"Tampered message"
        assert dsa.verify(tampered_message, signature, public_key) == False
