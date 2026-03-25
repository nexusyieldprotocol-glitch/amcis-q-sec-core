// Build script for API Gateway

fn main() {
    // Re-run if configuration changes
    println!("cargo:rerun-if-changed=config.toml");
    
    // Enable TLS 1.3 features
    println!("cargo:rustc-cfg=tls13");
}
