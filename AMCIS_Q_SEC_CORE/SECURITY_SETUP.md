# AMCIS Q-SEC CORE - Security Configuration

## 🔐 Encryption Status

### Master Encryption Keys
- **Location**: `.VAULT_MASTER/keys/`
- **Algorithm**: AES-256-GCM
- **Key File**: `amcis_master.key` (RESTRICTED ACCESS)
- **IV File**: `amcis_master.iv` (RESTRICTED ACCESS)

### Encrypted Directories
```
.VAULT_MASTER/
├── keys/              # Master encryption keys
├── encrypted_store/   # Encrypted sensitive files
└── security_report.json  # Security status
```

## 🛡️ Network Security

### Firewall Rules
| Rule | Direction | Action | Purpose |
|------|-----------|--------|---------|
| AMCIS-Allow-Loopback | Inbound | Allow | Local services |
| AMCIS-Allow-LAN | Inbound | Allow | Local network only |
| AMCIS-Block-RDP | Inbound | Block | Prevent remote desktop |
| AMCIS-Block-SMB | Inbound | Block | Prevent file sharing attacks |
| AMCIS-Block-NetBIOS | Inbound | Block | Legacy protocol blocking |

### Network Isolation
Run `network\amcis_network_lockdown.bat` as Administrator to:
- Block all unsolicited inbound connections
- Allow only localhost and LAN traffic
- Close vulnerable ports (RDP, SMB, NetBIOS)

## 🔑 File Encryption

### Encrypt a file
```bash
python crypto\amcis_encrypt.py encrypt path\to\file.txt -o encrypted\file.txt.enc
```

### Decrypt a file
```bash
python crypto\amcis_encrypt.py decrypt encrypted\file.txt.enc -o decrypted\file.txt
```

## 📊 Security Monitoring

### Check Security Status
```bash
python dashboard\security_monitor.py
```

This generates a security report including:
- Encryption key status
- File integrity hashes
- Network security status

## 🚨 Security Checklist

- [x] Master encryption keys generated
- [x] VAULT directory created with restricted permissions
- [x] File encryption module configured
- [x] Network firewall rules prepared
- [x] Access control restrictions applied
- [ ] Run network lockdown script (Admin required)
- [ ] Enable BitLocker (if supported)
- [ ] Regular security audits

## ⚠️ Important Notes

1. **Keep keys secure**: Never share `.VAULT_MASTER/keys/` contents
2. **Backup**: Store backup of keys offline in secure location
3. **Network**: Run lockdown script after confirming LAN connectivity needs
4. **Updates**: Regularly update AMCIS modules for latest security patches

## 📞 Emergency Procedures

### If keys are compromised:
1. Immediately regenerate keys
2. Re-encrypt all sensitive files
3. Review access logs
4. Rotate any exposed credentials

### If network breach suspected:
1. Run network lockdown script
2. Disconnect from network
3. Review firewall logs
4. Perform full security audit
