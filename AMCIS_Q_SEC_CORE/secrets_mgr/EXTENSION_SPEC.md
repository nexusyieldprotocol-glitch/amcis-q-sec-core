# 🔐 SECRETS MANAGER EXTENSION SPECIFICATION (G7)

**Version:** 1.0.0  
**Status:** DRAFT  
**Goal:** Integrate HashiCorp Vault as the primary secrets backend for the AMCIS ecosystem.

---

## 🏗️ 1. ARCHITECTURE
The `SecretsManager` will be refactored to support multiple backends via a `SecretsBackend` interface.

```python
class SecretsBackend(Protocol):
    def get_secret(self, name: str, version: Optional[int] = None) -> Optional[str]: ...
    def store_secret(self, name: str, value: str) -> bool: ...
    def list_secrets(self) -> List[str]: ...
```

---

## 🛡️ 2. BACKEND HIERARCHY
1. **Primary: `VaultBackend`**  
   - Connects to HashiCorp Vault via `VaultClient`.
   - Supports KV v2, PKI, and Dynamic DB credentials.
2. **Secondary/Fallback: `LocalBackend`**  
   - Uses the existing encrypted JSON storage in `/var/lib/amcis/secrets`.
   - Used when Vault is unreachable or for non-sensitive local config.

---

## 🔄 3. DYNAMIC CREDENTIALS
The extension will add support for Vault's dynamic credentials:

```python
def get_dynamic_db_creds(self, role: str) -> Dict[str, str]:
    """Retrieves ephemeral database credentials from Vault."""
    if self.vault_active:
        return self.vault.get_database_credentials(role)
    return self.local.get_db_creds(role) # Fallback to static
```

---

## 🔐 4. AUTOMATED ROTATION
- **Vault-Managed**: Rotation is handled by the Vault server. The extension will refresh credentials based on lease TTL.
- **Local-Managed**: `SecretsManager` maintains its current rotation callback logic for local keys.

---

## 📝 HANDOFF NOTES FOR KIMI
1. Refactor `SecretsManager.__init__` to accept a `VaultClient` instance.
2. Implement the `VaultBackend` wrapper class.
3. Update `get_secret` to try the `VaultBackend` first, then catch `VaultConnectionError` to fallback to `LocalBackend`.
4. Implement a "Sync" command to push local bootstrap secrets to Vault if they don't exist.
