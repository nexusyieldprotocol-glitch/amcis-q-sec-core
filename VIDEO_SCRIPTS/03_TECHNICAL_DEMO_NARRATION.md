# 🖥️ AMCIS TECHNICAL DEMO NARRATION SCRIPT
## Product Demonstration Video
**Target:** Technical evaluators, CISOs, engineering teams  
**Goal:** Showcase features, prove technical claims, generate evaluation interest  
**Tone:** Technical but accessible, confident, demo-focused  
**Length:** 8-10 minutes

---

## PRE-DEMO SETUP (0:00-0:30)

**[Visual: Clean desktop, terminal open, AMCIS dashboard loading]**

**SPEAKER:**
> "What you're about to see is the actual AMCIS platform running in a production-like environment. This isn't mocked up. This is real code, real functionality, real security operations. I'm going to walk you through four key capabilities: post-quantum cryptography, autonomous AI agents, compliance automation, and threat detection. Let's dive in."

**[Visual: AMCIS main dashboard loads - dark theme, professional UI]**

---

## SECTION 1: POST-QUANTUM CRYPTOGRAPHY (0:30-2:30)

### Key Generation Demo

**[Visual: Navigate to "Cryptography" → "Key Management" module]**

**SPEAKER:**
> "First, let's look at post-quantum cryptography. I'm opening the Key Management module. You'll see we support both classical algorithms for backward compatibility and NIST FIPS 203/204 post-quantum algorithms.
>
> Watch this. I'm generating a new ML-KEM-768 key pair—that's the NIST-standardized Module Lattice-based Key Encapsulation Mechanism. This algorithm is mathematically proven to be secure against quantum computer attacks using Shor's algorithm.
>
> [Click: "Generate New Key Pair"]
>
> The key is generated in the hardware security module, never exposed in memory, and automatically backed up with quantum-safe encryption. The entire operation took 47 milliseconds.
>
> Notice the key provenance trail—every operation is logged to our Merkle tree audit log with cryptographic integrity guarantees. If anyone tampers with this log, we can prove it."

**[Visual: Key generation animation, Merkle tree visualization, audit log entry]**

### Encryption/Decryption Demo

**[Visual: Switch to "Encryption Demo" tab]**

**SPEAKER:**
> "Now let's encrypt some data. I'll use a hybrid approach—combining classical ECDH for performance with ML-KEM for quantum safety. This gives us the best of both worlds: speed now, quantum safety later.
>
> [Type: "Classified project data - TOP SECRET"]
> [Click: Encrypt]
>
> The ciphertext you see here cannot be decrypted by any quantum computer—ever. Even when we have million-qubit machines, this encryption remains secure because it's based on lattice problems that quantum computers can't solve efficiently.
>
> Compare this to RSA-2048, which a quantum computer could break in about 8 hours. Our lattice-based encryption? Mathematically intractable, even for quantum."

**[Visual: Side-by-side comparison of RSA vs ML-KEM security levels]**

---

## SECTION 2: MULTI-AGENT AI ECOSYSTEM (2:30-5:00)

### Agent Overview

**[Visual: Navigate to "AI Agents" → "Agent Dashboard"]**

**SPEAKER:**
> "Now for the really cool part. AMCIS runs 35+ specialized AI agents that work together autonomously. Think of it as a security team that never sleeps, never takes vacation, and learns from every incident.
>
> This dashboard shows all active agents. The Orchestrator at the top routes tasks. Each colored bubble represents a specialist agent—threat detection, forensics, compliance, crypto operations, and so on.
>
> Watch the Memory Fabric in action. When one agent learns something, every other agent can access that knowledge through our secure, policy-governed memory system."

**[Visual: Animated agent network diagram, Memory Fabric visualization]**

### Live Threat Detection

**[Visual: Switch to "Threat Detection" agent view]**

**SPEAKER:**
> "Let me trigger a simulated attack and show you the autonomous response. I'm going to simulate a DNS tunneling attack—where an attacker exfiltrates data through DNS queries.
>
> [Click: "Inject Test Attack" → Select "DNS Tunneling"]
>
> The Telemetry Normalization Agent immediately detects the anomaly. Notice the spike in entropy here—legitimate DNS queries have low entropy, but encoded data has high entropy.
>
> The Threat Detection Agent scores this at 94% confidence. The SOAR Playbook Agent automatically triggers isolation procedures. And the Forensics Agent begins collecting evidence—all without human intervention.
>
> [Point to notification] The Orchestrator has escalated this to the SOC team because it exceeded our auto-remediation threshold. But the immediate threat is contained. Total response time: 3.2 seconds."

**[Visual: Real-time alerts, automatic containment actions, timeline of events]**

---

## SECTION 3: COMPLIANCE AUTOMATION (5:00-7:00)

### Framework Selection

**[Visual: Navigate to "Compliance" → "Frameworks"]**

**SPEAKER:**
> "Compliance audits are normally a nightmare—months of preparation, thousands of consulting hours, endless documentation. AMCIS automates this.
>
> We support CMMC 2.0, FedRAMP, PCI-DSS 4.0, HIPAA, NERC CIP, ISO 27001, and SOC 2—all out of the box. Let me show you NIST CSF 2.0.
>
> [Click: "NIST CSF 2.0"]
>
> You see all 108 controls mapped to your actual infrastructure. Green means compliant. Yellow means partially compliant. Red means non-compliant with remediation steps.
>
> The Compliance Audit Agent continuously monitors your environment and updates these scores in real-time. Not once a quarter—continuously."

**[Visual: NIST CSF 2.0 control mapping, compliance scores, trend charts]**

### Report Generation

**[Visual: Click "Generate Report"]**

**SPEAKER:**
> "When your auditor arrives, you don't scramble for spreadsheets. You click one button.
>
> [Click: "Generate Audit Package"]
>
> AMCIS produces a complete audit package: executive summary, control evidence, screenshot documentation, policy mappings, and the immutable audit log. Everything an auditor needs, generated in 4 minutes instead of 4 months.
>
> This report is digitally signed with post-quantum cryptography. The auditor can verify it hasn't been tampered with—even by a quantum computer."

**[Visual: Report generation progress, sample report pages, digital signature verification]**

---

## SECTION 4: ZERO-TRUST ARCHITECTURE (7:00-8:30)

### Network Visualization

**[Visual: Navigate to "Zero Trust" → "Network Topology"]**

**SPEAKER:**
> "Finally, let's look at zero-trust architecture. Traditional security trusts everything inside the firewall. Zero-trust trusts nothing—every request is verified, every time.
>
> This visualization shows your entire infrastructure—cloud, on-premise, edge devices. Every line you see is an encrypted, authenticated connection. There are no trusted zones. Every microsegment is isolated.
>
> [Hover over a node] This is a database server. It can only accept connections from these three specific services, using these specific certificates, from these specific IP ranges, at these specific times. Any deviation is automatically blocked."

**[Visual: Interactive 3D network topology, microsegment boundaries, policy enforcement points]**

### Policy Enforcement

**[Visual: Click on a policy rule]**

**SPEAKER:**
> "Let me show you policy enforcement in action. This rule says: 'Database servers reject all connections except from the API tier, using mTLS with quantum-safe certificates, during business hours only.'
>
> [Switch to terminal] I'll try to connect directly to the database from an unauthorized location.
>
> [Type: ssh db-server]
>
> Blocked. Instantly. The Identity and Access Agent rejected the connection before it even reached the database. The attempt is logged, an alert is sent to the SOC, and the source IP is added to the watch list.
>
> That's zero-trust. Verify explicitly. Use least privilege. Assume breach."

**[Visual: Terminal showing connection rejection, alert generation, automatic response]**

---

## CONCLUSION & CALL-TO-ACTION (8:30-9:00)

**[Visual: Return to main dashboard, pan across all modules]**

**SPEAKER:**
> "What you've seen is just a fraction of AMCIS's capabilities. Post-quantum cryptography that survives the quantum era. 35 AI agents working autonomously. Compliance automation that turns months into minutes. Zero-trust architecture that assumes breach and prevents it anyway.
>
> This isn't a roadmap. This is shipping code. Docker containers ready to deploy. APIs fully documented. Test suites passing. Production-hardened.
>
> If you're evaluating cybersecurity platforms, if you're facing NIST compliance deadlines, if you're worried about quantum threats—AMCIS is ready. Let's schedule a personalized demo where we can explore your specific use cases.
>
> Thank you for watching."

**[Visual: AMCIS logo, contact information, QR code to schedule demo]**

---

## TECHNICAL PRODUCTION NOTES

### Recording Setup
- **Screen capture:** 4K resolution, 60fps
- **Audio:** Professional microphone, noise-free environment
- **Cursor:** Highlighted with click ripples
- **Zoom:** Smooth zoom on important UI elements

### Post-Production
- **B-roll:** Supplement with architecture diagrams
- **Captions:** Key metrics and numbers
- **Pacing:** Cut pauses, speed up loading screens
- **Music:** Subtle, under 15% volume

### Accessibility
- Closed captions available
- High contrast UI mode shown
- Keyboard navigation demonstrated

---

## DEMO ENVIRONMENT REQUIREMENTS

**Minimum viable demo:**
- 1 AMCIS core instance
- Sample data pre-loaded
- 3-4 test scenarios scripted
- Rollback capability for repeated demos

**Full production demo:**
- Multi-node cluster
- Real-time threat feeds
- Live compliance monitoring
- Integration with customer tools (if known)

---

## HANDLING DEMO FAILURES

**If something breaks during live demo:**
1. Acknowledge: "That's interesting—let me check that."
2. Pivot: "While that loads, let me show you..."
3. Have screenshots/video backup ready
4. Follow up: "I'll send you a recording of this working."

**Golden rule:** Never apologize more than once. Stay confident.
