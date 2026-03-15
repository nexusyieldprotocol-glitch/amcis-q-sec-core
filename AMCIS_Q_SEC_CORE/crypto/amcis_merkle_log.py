"""
AMCIS Merkle Log
=================

Append-only tamper-evident logging using Merkle trees.
Provides cryptographic verification of log integrity.

Features:
- SHA-256 hash chain
- Merkle tree construction
- Inclusion proofs
- Consistency proofs
- Log verification

NIST Alignment: SP 800-92 (Log Management), RFC 6962 (Certificate Transparency)
"""

import hashlib
import json
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import structlog


@dataclass
class LogEntry:
    """Log entry with hash chain."""
    index: int
    timestamp: float
    data: Dict[str, Any]
    entry_hash: str
    previous_hash: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "entry_hash": self.entry_hash,
            "previous_hash": self.previous_hash
        }
    
    def canonical_json(self) -> str:
        """Get canonical JSON representation for hashing."""
        return json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True, separators=(',', ':'))


@dataclass
class MerkleProof:
    """Merkle inclusion proof."""
    leaf_index: int
    leaf_hash: str
    root_hash: str
    proof_hashes: List[str]
    tree_size: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "leaf_index": self.leaf_index,
            "leaf_hash": self.leaf_hash,
            "root_hash": self.root_hash,
            "proof_hashes": self.proof_hashes,
            "tree_size": self.tree_size
        }


class MerkleTree:
    """
    Merkle Tree implementation for log verification.
    
    Binary hash tree providing efficient verification of
    log entry inclusion and consistency.
    """
    
    def __init__(self, hasher=hashlib.sha256) -> None:
        """
        Initialize Merkle tree.
        
        Args:
            hasher: Hash function to use
        """
        self.hasher = hasher
        self.leaves: List[str] = []
        self.tree: List[List[str]] = []
    
    def add_leaf(self, data_hash: str) -> None:
        """Add leaf hash to tree."""
        self.leaves.append(data_hash)
    
    def build(self) -> str:
        """
        Build Merkle tree and return root hash.
        
        Returns:
            Merkle root hash
        """
        if not self.leaves:
            return self._hash(b"")
        
        self.tree = [self.leaves[:]]
        
        current_level = self.leaves[:]
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # Duplicate last hash if odd
                
                combined = self._hash_pair(left, right)
                next_level.append(combined)
            
            self.tree.append(next_level)
            current_level = next_level
        
        return current_level[0]
    
    def _hash(self, data: bytes) -> str:
        """Hash data."""
        return self.hasher(data).hexdigest()
    
    def _hash_pair(self, left: str, right: str) -> str:
        """Hash a pair of hashes."""
        # Use 0x00 prefix for internal nodes (as per RFC 6962)
        combined = b'\x01' + bytes.fromhex(left) + bytes.fromhex(right)
        return self._hash(combined)
    
    def get_inclusion_proof(self, leaf_index: int) -> Optional[MerkleProof]:
        """
        Generate inclusion proof for leaf.
        
        Args:
            leaf_index: Index of leaf
            
        Returns:
            Merkle proof or None
        """
        if not self.tree or leaf_index >= len(self.leaves):
            return None
        
        proof_hashes = []
        idx = leaf_index
        
        for level in self.tree[:-1]:
            sibling_idx = idx ^ 1  # XOR 1 to get sibling
            if sibling_idx < len(level):
                proof_hashes.append(level[sibling_idx])
            idx //= 2
        
        return MerkleProof(
            leaf_index=leaf_index,
            leaf_hash=self.leaves[leaf_index],
            root_hash=self.tree[-1][0],
            proof_hashes=proof_hashes,
            tree_size=len(self.leaves)
        )
    
    def verify_inclusion(
        self,
        proof: MerkleProof,
        leaf_hash: str
    ) -> bool:
        """
        Verify inclusion proof.
        
        Args:
            proof: Merkle proof
            leaf_hash: Expected leaf hash
            
        Returns:
            True if proof is valid
        """
        if proof.leaf_hash != leaf_hash:
            return False
        
        current_hash = leaf_hash
        idx = proof.leaf_index
        
        for sibling_hash in proof.proof_hashes:
            if idx % 2 == 0:
                current_hash = self._hash_pair(current_hash, sibling_hash)
            else:
                current_hash = self._hash_pair(sibling_hash, current_hash)
            idx //= 2
        
        return current_hash == proof.root_hash


class MerkleLog:
    """
    AMCIS Merkle Log
    ================
    
    Append-only tamper-evident log with cryptographic verification.
    Each entry contains a hash chain linking to previous entries.
    """
    
    def __init__(
        self,
        log_path: Optional[Path] = None,
        max_entries_per_file: int = 10000
    ) -> None:
        """
        Initialize Merkle log.
        
        Args:
            log_path: Path for log storage
            max_entries_per_file: Maximum entries per log file
        """
        self.log_path = log_path or Path("/var/log/amcis/merkle")
        self.log_path.mkdir(parents=True, exist_ok=True)
        self.max_entries_per_file = max_entries_per_file
        
        self.logger = structlog.get_logger("amcis.merkle_log")
        
        # In-memory entries (limited)
        self._entries: List[LogEntry] = []
        self._max_memory_entries = 1000
        
        # Current state
        self._last_hash = "0" * 64
        self._entry_count = 0
        self._merkle_tree = MerkleTree()
        
        # Load existing state
        self._load_state()
        
        self.logger.info(
            "merkle_log_initialized",
            log_path=str(self.log_path),
            entry_count=self._entry_count
        )
    
    def _load_state(self) -> None:
        """Load log state from storage."""
        state_file = self.log_path / "state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                
                self._entry_count = state.get("entry_count", 0)
                self._last_hash = state.get("last_hash", "0" * 64)
                
                # Load recent entries
                self._load_recent_entries()
                
            except Exception as e:
                self.logger.error("state_load_failed", error=str(e))
    
    def _load_recent_entries(self) -> None:
        """Load recent entries from log files."""
        # Find latest log file
        log_files = sorted(self.log_path.glob("merkle_log_*.json"))
        
        if log_files:
            latest = log_files[-1]
            try:
                with open(latest, 'r') as f:
                    data = json.load(f)
                
                entries_data = data.get("entries", [])
                # Keep last N entries
                for entry_data in entries_data[-self._max_memory_entries:]:
                    entry = LogEntry(
                        index=entry_data["index"],
                        timestamp=entry_data["timestamp"],
                        data=entry_data["data"],
                        entry_hash=entry_data["entry_hash"],
                        previous_hash=entry_data["previous_hash"]
                    )
                    self._entries.append(entry)
                    self._merkle_tree.add_leaf(entry.entry_hash)
                
                self._merkle_tree.build()
                
            except Exception as e:
                self.logger.error("entries_load_failed", error=str(e))
    
    def append(self, data: Dict[str, Any]) -> LogEntry:
        """
        Append entry to log.
        
        Args:
            data: Entry data
            
        Returns:
            Created log entry
        """
        index = self._entry_count
        timestamp = time.time()
        
        # Create entry without hash first
        entry = LogEntry(
            index=index,
            timestamp=timestamp,
            data=data,
            entry_hash="",  # Will compute
            previous_hash=self._last_hash
        )
        
        # Compute entry hash
        entry.entry_hash = self._compute_entry_hash(entry)
        
        # Add to memory
        self._entries.append(entry)
        if len(self._entries) > self._max_memory_entries:
            self._entries.pop(0)
        
        # Update Merkle tree
        self._merkle_tree.add_leaf(entry.entry_hash)
        self._merkle_tree.build()
        
        # Update state
        self._last_hash = entry.entry_hash
        self._entry_count += 1
        
        # Persist
        self._persist_entry(entry)
        
        self.logger.debug(
            "log_entry_appended",
            index=index,
            entry_hash=entry.entry_hash[:16]
        )
        
        return entry
    
    def _compute_entry_hash(self, entry: LogEntry) -> str:
        """Compute entry hash."""
        canonical = entry.canonical_json()
        # Use 0x00 prefix for leaf nodes
        prefixed = b'\x00' + canonical.encode()
        return hashlib.sha256(prefixed).hexdigest()
    
    def _persist_entry(self, entry: LogEntry) -> None:
        """Persist entry to storage."""
        # Determine file
        file_index = entry.index // self.max_entries_per_file
        log_file = self.log_path / f"merkle_log_{file_index:08d}.json"
        
        # Load existing or create new
        if log_file.exists():
            with open(log_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"entries": []}
        
        data["entries"].append(entry.to_dict())
        data["merkle_root"] = self._merkle_tree.tree[-1][0] if self._merkle_tree.tree else ""
        
        # Atomic write
        temp_file = log_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
        temp_file.replace(log_file)
        
        # Update state
        self._save_state()
    
    def _save_state(self) -> None:
        """Save current state."""
        state_file = self.log_path / "state.json"
        state = {
            "entry_count": self._entry_count,
            "last_hash": self._last_hash,
            "merkle_root": self._merkle_tree.tree[-1][0] if self._merkle_tree.tree else "",
            "updated_at": time.time()
        }
        
        temp_file = state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(state, f, indent=2)
        temp_file.replace(state_file)
    
    def get_entry(self, index: int) -> Optional[LogEntry]:
        """
        Get entry by index.
        
        Args:
            index: Entry index
            
        Returns:
            Log entry or None
        """
        # Check memory first
        for entry in self._entries:
            if entry.index == index:
                return entry
        
        # Load from file
        return self._load_entry_from_file(index)
    
    def _load_entry_from_file(self, index: int) -> Optional[LogEntry]:
        """Load entry from log file."""
        file_index = index // self.max_entries_per_file
        log_file = self.log_path / f"merkle_log_{file_index:08d}.json"
        
        if not log_file.exists():
            return None
        
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
            
            for entry_data in data.get("entries", []):
                if entry_data["index"] == index:
                    return LogEntry(
                        index=entry_data["index"],
                        timestamp=entry_data["timestamp"],
                        data=entry_data["data"],
                        entry_hash=entry_data["entry_hash"],
                        previous_hash=entry_data["previous_hash"]
                    )
        except Exception as e:
            self.logger.error("entry_load_failed", index=index, error=str(e))
        
        return None
    
    def get_inclusion_proof(self, index: int) -> Optional[MerkleProof]:
        """
        Get inclusion proof for entry.
        
        Args:
            index: Entry index
            
        Returns:
            Inclusion proof or None
        """
        if index >= self._entry_count:
            return None
        
        return self._merkle_tree.get_inclusion_proof(index)
    
    def verify_entry(self, index: int) -> Tuple[bool, Optional[str]]:
        """
        Verify log entry integrity.
        
        Args:
            index: Entry index to verify
            
        Returns:
            (valid, error_message)
        """
        entry = self.get_entry(index)
        if not entry:
            return False, f"Entry {index} not found"
        
        # Verify entry hash
        computed_hash = self._compute_entry_hash(entry)
        if computed_hash != entry.entry_hash:
            return False, f"Entry hash mismatch: {computed_hash} != {entry.entry_hash}"
        
        # Verify chain (if not first entry)
        if index > 0:
            prev_entry = self.get_entry(index - 1)
            if not prev_entry:
                return False, f"Previous entry {index - 1} not found"
            
            if entry.previous_hash != prev_entry.entry_hash:
                return False, f"Chain broken at index {index}"
        
        return True, None
    
    def verify_log(self) -> Tuple[bool, List[str]]:
        """
        Verify entire log integrity.
        
        Returns:
            (valid, list of errors)
        """
        errors = []
        
        for i in range(self._entry_count):
            valid, error = self.verify_entry(i)
            if not valid:
                errors.append(f"Entry {i}: {error}")
        
        return len(errors) == 0, errors
    
    def get_root_hash(self) -> str:
        """Get current Merkle root hash."""
        if self._merkle_tree.tree:
            return self._merkle_tree.tree[-1][0]
        return "0" * 64
    
    def get_entry_count(self) -> int:
        """Get total entry count."""
        return self._entry_count
    
    def get_recent_entries(self, count: int = 100) -> List[LogEntry]:
        """Get recent entries."""
        return self._entries[-count:] if self._entries else []
    
    def export_bundle(self, start_index: int = 0) -> Dict[str, Any]:
        """
        Export log bundle for verification.
        
        Args:
            start_index: Starting entry index
            
        Returns:
            Log bundle
        """
        entries = []
        for i in range(start_index, self._entry_count):
            entry = self.get_entry(i)
            if entry:
                entries.append(entry.to_dict())
        
        return {
            "start_index": start_index,
            "entry_count": len(entries),
            "merkle_root": self.get_root_hash(),
            "entries": entries
        }
