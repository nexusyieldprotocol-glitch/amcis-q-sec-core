//! Integration tests for PQC cryptography

use amcis_crypto_pqc::{kyber::MlKem, dilithium::MlDsa};

#[test]
fn test_kyber768_full_roundtrip() {
    // Generate keypair
    let keypair = MlKem::keygen768().expect("Keygen should succeed");
    
    // Encapsulate
    let encap = MlKem::encapsulate768(&keypair.public_key)
        .expect("Encapsulation should succeed");
    
    // Decapsulate
    let decap = MlKem::decapsulate768(&encap.ciphertext, &keypair.secret_key)
        .expect("Decapsulation should succeed");
    
    // Verify shared secrets match
    assert_eq!(encap.shared_secret, decap, "Shared secrets must match");
}

#[test]
fn test_dilithium65_sign_verify() {
    let keypair = MlDsa::keygen65().expect("Keygen should succeed");
    let message = b"AMCIS test message";
    
    // Sign
    let signature = MlDsa::sign65(message, &keypair.secret_key)
        .expect("Signing should succeed");
    
    // Verify
    let valid = MlDsa::verify65(message, &signature, &keypair.public_key)
        .expect("Verification should succeed");
    
    assert!(valid, "Signature should be valid");
}

#[test]
fn test_dilithium_wrong_message_fails() {
    let keypair = MlDsa::keygen65().unwrap();
    let message = b"Original message";
    let wrong_message = b"Tampered message";
    
    let signature = MlDsa::sign65(message, &keypair.secret_key).unwrap();
    let valid = MlDsa::verify65(wrong_message, &signature, &keypair.public_key).unwrap();
    
    assert!(!valid, "Tampered message should fail verification");
}

#[test]
fn test_kyber_multiple_encapsulations() {
    let keypair = MlKem::keygen768().unwrap();
    
    // Multiple encapsulations should produce different ciphertexts
    let encap1 = MlKem::encapsulate768(&keypair.public_key).unwrap();
    let encap2 = MlKem::encapsulate768(&keypair.public_key).unwrap();
    
    assert_ne!(encap1.ciphertext, encap2.ciphertext, "Ciphertexts should be different");
    
    // But both should decapsulate successfully
    let ss1 = MlKem::decapsulate768(&encap1.ciphertext, &keypair.secret_key).unwrap();
    let ss2 = MlKem::decapsulate768(&encap2.ciphertext, &keypair.secret_key).unwrap();
    
    assert_eq!(ss1, encap1.shared_secret, "First shared secret should match");
    assert_eq!(ss2, encap2.shared_secret, "Second shared secret should match");
}
