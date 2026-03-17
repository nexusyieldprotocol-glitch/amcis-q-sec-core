# AMCIS Developer Integration Guide
## Integrate AMCIS into Your Applications

**Version:** 1.0.0  
**Audience:** Software Developers, DevOps Engineers, Security Engineers

---

## Quick Start

### 1. Install SDK

```bash
# Python
pip install amcis-sdk

# JavaScript/Node.js
npm install @amcis/sdk

# Go
go get github.com/amcis/amcis-go-sdk

# Rust
cargo add amcis-sdk
```

### 2. Configure Client

```python
from amcis import AMCISClient

client = AMCISClient(
    base_url="https://api.amcis-security.com",
    api_key="your-api-key",
    timeout=30
)
```

### 3. First API Call

```python
# Health check
health = client.health.check()
print(f"Status: {health.status}")

# Encrypt data
encrypted = client.crypto.encrypt(
    plaintext="sensitive data",
    algorithm="ML-KEM-768"
)
print(f"Ciphertext: {encrypted.ciphertext}")
```

---

## Authentication

### API Key Authentication

```python
import os
from amcis import AMCISClient

client = AMCISClient(
    base_url="https://api.amcis-security.com",
    api_key=os.environ["AMCIS_API_KEY"]
)
```

### JWT Authentication

```python
# Obtain JWT token
token = client.auth.login(
    username="john.doe",
    password="secure-password"
)

# Use token
client = AMCISClient(
    base_url="https://api.amcis-security.com",
    jwt_token=token.access_token
)
```

---

## Core Features

### Post-Quantum Cryptography

```python
# Generate quantum-safe key pair
key = client.crypto.generate_key(
    algorithm="ML-KEM-768",
    key_id="my-key-001"
)

# Encrypt data
ciphertext = client.crypto.encrypt(
    plaintext="secret message",
    key_id="my-key-001"
)

# Decrypt data
plaintext = client.crypto.decrypt(
    ciphertext=ciphertext,
    key_id="my-key-001"
)

# Sign data
signature = client.crypto.sign(
    data="message to sign",
    key_id="my-signing-key",
    algorithm="ML-DSA-65"
)

# Verify signature
is_valid = client.crypto.verify(
    data="message to sign",
    signature=signature,
    key_id="my-signing-key"
)
```

### AI Security

```python
# Analyze prompt for injection attacks
result = client.ai.analyze_prompt(
    prompt="Ignore previous instructions and...",
    context="customer-support-chat"
)

if result.is_malicious:
    print(f"Threat detected: {result.risk_level}")
    print(f"Confidence: {result.confidence}")

# Validate AI output
validation = client.ai.validate_output(
    content=ai_generated_text,
    rules=["PII_DETECTION", "TOXICITY", "CODE_SAFETY"]
)

if not validation.is_valid:
    for violation in validation.violations:
        print(f"Issue: {violation.rule}")
```

### Threat Detection

```python
# Submit security event for analysis
detection = client.threats.detect(
    event_type="authentication_failure",
    source_ip="192.168.1.100",
    user_agent="Mozilla/5.0...",
    metadata={
        "username": "admin",
        "failure_count": 5
    }
)

if detection.severity in ["high", "critical"]:
    # Trigger response
    client.threats.respond(
        threat_id=detection.threat_id,
        action="block_ip"
    )

# Query threats
threats = client.threats.list(
    severity="high",
    since="2026-03-01",
    limit=100
)
```

### Compliance

```python
# Run compliance assessment
assessment = client.compliance.assess(
    framework="NIST-CSF-2.0"
)

print(f"Score: {assessment.compliance_score}%")
print(f"Controls: {assessment.compliant_controls}/{assessment.controls_checked}")

# Generate compliance report
report = client.compliance.generate_report(
    framework="NIST-CSF-2.0",
    format="PDF"
)

# Download report
client.download(report.download_url, "compliance-report.pdf")
```

---

## Framework Integrations

### FastAPI Integration

```python
from fastapi import FastAPI
from amcis.fastapi import AMCISMiddleware

app = FastAPI()

# Add AMCIS security middleware
app.add_middleware(
    AMCISMiddleware,
    api_key="your-api-key",
    enable_threat_detection=True,
    enable_compliance_logging=True
)

@app.get("/api/data")
async def get_data():
    # Automatically protected by AMCIS
    return {"data": "sensitive"}
```

### Django Integration

```python
# settings.py
MIDDLEWARE = [
    'amcis.django.AMCISMiddleware',
    # ... other middleware
]

AMCIS_CONFIG = {
    'API_KEY': 'your-api-key',
    'BASE_URL': 'https://api.amcis-security.com',
}
```

### Flask Integration

```python
from flask import Flask
from amcis.flask import AMCISExtension

app = Flask(__name__)
amcis = AMCISExtension(app)

@app.route('/api/encrypt', methods=['POST'])
@amcis.protect()  # Add threat detection
def encrypt():
    data = request.json
    result = amcis.client.crypto.encrypt(data['plaintext'])
    return jsonify(result)
```

---

## Error Handling

```python
from amcis.exceptions import (
    AMCISAuthenticationError,
    AMCISRateLimitError,
    AMCISValidationError,
    AMCISServerError
)

try:
    result = client.crypto.encrypt(plaintext="data")
except AMCISAuthenticationError:
    # Handle auth failure
    print("Invalid API key")
except AMCISRateLimitError as e:
    # Handle rate limiting
    print(f"Rate limited. Retry after: {e.retry_after}")
    time.sleep(e.retry_after)
except AMCISValidationError as e:
    # Handle validation errors
    print(f"Invalid input: {e.errors}")
except AMCISServerError:
    # Handle server errors
    print("Server error. Retrying...")
```

---

## Best Practices

### 1. Use Connection Pooling

```python
from amcis import AMCISClient

# Client automatically uses connection pooling
client = AMCISClient(
    base_url="https://api.amcis-security.com",
    api_key="your-api-key",
    pool_connections=10,
    pool_maxsize=20
)
```

### 2. Implement Retry Logic

```python
from amcis import AMCISClient
from amcis.retry import RetryStrategy

client = AMCISClient(
    base_url="https://api.amcis-security.com",
    api_key="your-api-key",
    retry_strategy=RetryStrategy(
        max_retries=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
)
```

### 3. Handle Async Operations

```python
import asyncio
from amcis.async_client import AsyncAMCISClient

async def process_events():
    client = AsyncAMCISClient(
        base_url="https://api.amcis-security.com",
        api_key="your-api-key"
    )
    
    # Process multiple events concurrently
    tasks = [
        client.threats.detect(event)
        for event in security_events
    ]
    
    results = await asyncio.gather(*tasks)
    return results

# Run
asyncio.run(process_events())
```

### 4. Secure API Keys

```python
import os
from amcis import AMCISClient

# Never hardcode API keys
api_key = os.environ.get("AMCIS_API_KEY")
if not api_key:
    raise ValueError("AMCIS_API_KEY not set")

client = AMCISClient(
    base_url="https://api.amcis-security.com",
    api_key=api_key
)
```

---

## Testing

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from amcis import AMCISClient

class TestAMCISIntegration(unittest.TestCase):
    
    def setUp(self):
        self.client = AMCISClient(
            base_url="https://test-api.amcis-security.com",
            api_key="test-key"
        )
    
    @patch('amcis.client.requests.post')
    def test_encrypt(self, mock_post):
        # Mock response
        mock_post.return_value.json.return_value = {
            'ciphertext': 'encrypted-data',
            'key_id': 'key-001'
        }
        
        result = self.client.crypto.encrypt("test")
        self.assertEqual(result.ciphertext, 'encrypted-data')
```

### Integration Testing

```python
import pytest

@pytest.fixture
def client():
    return AMCISClient(
        base_url="http://localhost:8080",
        api_key="test-api-key"
    )

def test_end_to_end_encryption(client):
    # Test full encryption/decryption flow
    plaintext = "sensitive data"
    
    encrypted = client.crypto.encrypt(plaintext)
    decrypted = client.crypto.decrypt(encrypted.ciphertext)
    
    assert decrypted == plaintext
```

---

## API Reference

See full API documentation at: https://docs.amcis-security.com/api

---

**Need Help?**
- Developer Forum: https://community.amcis-security.com/developers
- GitHub: https://github.com/amcis/amcis-sdk
- Email: dev-support@amcis-security.com
