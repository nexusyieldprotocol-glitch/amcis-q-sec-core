"""
AMCIS RAG Provenance Tracker
=============================

Retrieval-Augmented Generation (RAG) provenance tracking for
ensuring document authenticity and source verification.

Features:
- Document signature validation
- Source chain tracking
- Content integrity verification
- Provenance graph construction

NIST Alignment: AI RMF (Risk Management Framework)
"""

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from urllib.parse import urlparse

import structlog


class DocumentType(Enum):
    """Types of source documents."""
    PDF = auto()
    WEBPAGE = auto()
    MARKDOWN = auto()
    JSON = auto()
    XML = auto()
    DATABASE = auto()
    API_RESPONSE = auto()
    UNKNOWN = auto()


class VerificationStatus(Enum):
    """Document verification status."""
    UNVERIFIED = auto()
    PENDING = auto()
    VERIFIED = auto()
    FAILED = auto()
    EXPIRED = auto()


@dataclass
class DocumentSignature:
    """Document cryptographic signature."""
    algorithm: str
    signature: str
    public_key_fingerprint: Optional[str]
    timestamp: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "algorithm": self.algorithm,
            "signature": self.signature[:64] + "..." if len(self.signature) > 64 else self.signature,
            "public_key_fingerprint": self.public_key_fingerprint,
            "timestamp": self.timestamp
        }


@dataclass
class SourceDocument:
    """Source document metadata."""
    doc_id: str
    uri: str
    doc_type: DocumentType
    content_hash: str
    size_bytes: int
    retrieved_at: float
    last_modified: Optional[float]
    etag: Optional[str]
    signatures: List[DocumentSignature] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "doc_id": self.doc_id,
            "uri": self.uri,
            "doc_type": self.doc_type.name,
            "content_hash": self.content_hash[:16] + "...",
            "size_bytes": self.size_bytes,
            "retrieved_at": self.retrieved_at,
            "signatures": [s.to_dict() for s in self.signatures],
            "metadata": self.metadata
        }


@dataclass
class ProvenanceRecord:
    """Provenance record for RAG context."""
    record_id: str
    query: str
    retrieved_documents: List[SourceDocument]
    retrieval_timestamp: float
    retrieval_method: str
    confidence_scores: Dict[str, float]
    verification_status: VerificationStatus
    provenance_chain: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "record_id": self.record_id,
            "query": self.query[:100] + "..." if len(self.query) > 100 else self.query,
            "document_count": len(self.retrieved_documents),
            "retrieval_timestamp": self.retrieval_timestamp,
            "retrieval_method": self.retrieval_method,
            "verification_status": self.verification_status.name,
            "provenance_chain": self.provenance_chain
        }


class RAGProvenance:
    """
    AMCIS RAG Provenance
    ====================
    
    Document provenance tracking for RAG systems ensuring
    source authenticity and content integrity.
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        verification_ttl: float = 86400  # 24 hours
    ) -> None:
        """
        Initialize RAG provenance tracker.
        
        Args:
            storage_path: Path for provenance storage
            verification_ttl: Time-to-live for verifications
        """
        self.storage_path = storage_path or Path("/var/lib/amcis/provenance")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.verification_ttl = verification_ttl
        
        self.logger = structlog.get_logger("amcis.rag_provenance")
        
        # Storage
        self._documents: Dict[str, SourceDocument] = {}
        self._records: Dict[str, ProvenanceRecord] = {}
        
        # Verification cache
        self._verification_cache: Dict[str, Tuple[VerificationStatus, float]] = {}
        
        # Signature validators
        self._validators: Dict[str, Callable[[SourceDocument], bool]] = {}
        
        # Load existing data
        self._load_data()
        
        self.logger.info("rag_provenance_initialized")
    
    def _load_data(self) -> None:
        """Load existing provenance data."""
        docs_file = self.storage_path / "documents.json"
        if docs_file.exists():
            try:
                with open(docs_file, 'r') as f:
                    data = json.load(f)
                
                for doc_id, doc_data in data.get("documents", {}).items():
                    self._documents[doc_id] = SourceDocument(
                        doc_id=doc_data["doc_id"],
                        uri=doc_data["uri"],
                        doc_type=DocumentType[doc_data["doc_type"]],
                        content_hash=doc_data["content_hash"],
                        size_bytes=doc_data["size_bytes"],
                        retrieved_at=doc_data["retrieved_at"],
                        last_modified=doc_data.get("last_modified"),
                        etag=doc_data.get("etag"),
                        metadata=doc_data.get("metadata", {})
                    )
                
                self.logger.info("provenance_data_loaded", docs=len(self._documents))
                
            except Exception as e:
                self.logger.error("data_load_failed", error=str(e))
    
    def _save_data(self) -> None:
        """Save provenance data."""
        try:
            data = {
                "documents": {
                    doc_id: {
                        "doc_id": doc.doc_id,
                        "uri": doc.uri,
                        "doc_type": doc.doc_type.name,
                        "content_hash": doc.content_hash,
                        "size_bytes": doc.size_bytes,
                        "retrieved_at": doc.retrieved_at,
                        "last_modified": doc.last_modified,
                        "etag": doc.etag,
                        "metadata": doc.metadata
                    }
                    for doc_id, doc in self._documents.items()
                },
                "updated_at": time.time()
            }
            
            docs_file = self.storage_path / "documents.json"
            temp_file = docs_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2)
            temp_file.replace(docs_file)
            
        except Exception as e:
            self.logger.error("data_save_failed", error=str(e))
    
    def register_document(
        self,
        uri: str,
        content: bytes,
        doc_type: Optional[DocumentType] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SourceDocument:
        """
        Register a source document.
        
        Args:
            uri: Document URI
            content: Document content
            doc_type: Document type
            metadata: Additional metadata
            
        Returns:
            Registered document
        """
        # Detect type if not specified
        if doc_type is None:
            doc_type = self._detect_document_type(uri, content)
        
        # Generate document ID
        content_hash = hashlib.sha3_256(content).hexdigest()
        doc_id = f"doc_{content_hash[:16]}"
        
        # Check if already exists
        if doc_id in self._documents:
            existing = self._documents[doc_id]
            self.logger.debug("document_already_registered", doc_id=doc_id)
            return existing
        
        document = SourceDocument(
            doc_id=doc_id,
            uri=uri,
            doc_type=doc_type,
            content_hash=content_hash,
            size_bytes=len(content),
            retrieved_at=time.time(),
            metadata=metadata or {}
        )
        
        self._documents[doc_id] = document
        self._save_data()
        
        self.logger.info(
            "document_registered",
            doc_id=doc_id,
            uri=uri,
            doc_type=doc_type.name
        )
        
        return document
    
    def _detect_document_type(self, uri: str, content: bytes) -> DocumentType:
        """Detect document type from URI and content."""
        uri_lower = uri.lower()
        
        if uri_lower.endswith('.pdf'):
            return DocumentType.PDF
        elif uri_lower.endswith(('.md', '.markdown')):
            return DocumentType.MARKDOWN
        elif uri_lower.endswith('.json'):
            return DocumentType.JSON
        elif uri_lower.endswith('.xml'):
            return DocumentType.XML
        elif uri_lower.startswith(('http://', 'https://')):
            return DocumentType.WEBPAGE
        elif uri_lower.startswith(('db://', 'database://')):
            return DocumentType.DATABASE
        
        # Try content-based detection
        if content[:4] == b'%PDF':
            return DocumentType.PDF
        elif content[:5] == b'<?xml':
            return DocumentType.XML
        
        return DocumentType.UNKNOWN
    
    def add_signature(
        self,
        doc_id: str,
        algorithm: str,
        signature: str,
        public_key_fingerprint: Optional[str] = None
    ) -> bool:
        """
        Add signature to document.
        
        Args:
            doc_id: Document ID
            algorithm: Signature algorithm
            signature: Signature value
            public_key_fingerprint: Key fingerprint
            
        Returns:
            True if added
        """
        document = self._documents.get(doc_id)
        if not document:
            return False
        
        sig = DocumentSignature(
            algorithm=algorithm,
            signature=signature,
            public_key_fingerprint=public_key_fingerprint,
            timestamp=time.time()
        )
        
        document.signatures.append(sig)
        self._save_data()
        
        self.logger.info("signature_added", doc_id=doc_id, algorithm=algorithm)
        return True
    
    def verify_document(self, doc_id: str, content: Optional[bytes] = None) -> VerificationStatus:
        """
        Verify document integrity.
        
        Args:
            doc_id: Document ID
            content: Optional content to verify against
            
        Returns:
            Verification status
        """
        document = self._documents.get(doc_id)
        if not document:
            return VerificationStatus.FAILED
        
        # Check cache
        cached = self._verification_cache.get(doc_id)
        if cached:
            status, timestamp = cached
            if time.time() - timestamp < self.verification_ttl:
                return status
        
        status = VerificationStatus.UNVERIFIED
        
        # If content provided, verify hash
        if content is not None:
            content_hash = hashlib.sha3_256(content).hexdigest()
            if content_hash == document.content_hash:
                status = VerificationStatus.VERIFIED
            else:
                status = VerificationStatus.FAILED
        
        # Run signature validators
        for sig in document.signatures:
            validator = self._validators.get(sig.algorithm)
            if validator:
                if validator(document):
                    status = VerificationStatus.VERIFIED
                else:
                    status = VerificationStatus.FAILED
        
        # Cache result
        self._verification_cache[doc_id] = (status, time.time())
        
        return status
    
    def create_provenance_record(
        self,
        query: str,
        document_ids: List[str],
        retrieval_method: str = "semantic_search",
        confidence_scores: Optional[Dict[str, float]] = None
    ) -> ProvenanceRecord:
        """
        Create provenance record for RAG retrieval.
        
        Args:
            query: User query
            document_ids: Retrieved document IDs
            retrieval_method: Method used for retrieval
            confidence_scores: Retrieval confidence scores
            
        Returns:
            Provenance record
        """
        record_id = f"rec_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Collect documents
        documents = []
        for doc_id in document_ids:
            doc = self._documents.get(doc_id)
            if doc:
                documents.append(doc)
        
        # Determine verification status
        statuses = [self.verify_document(doc.doc_id) for doc in documents]
        
        if all(s == VerificationStatus.VERIFIED for s in statuses):
            verification_status = VerificationStatus.VERIFIED
        elif any(s == VerificationStatus.FAILED for s in statuses):
            verification_status = VerificationStatus.FAILED
        else:
            verification_status = VerificationStatus.UNVERIFIED
        
        record = ProvenanceRecord(
            record_id=record_id,
            query=query,
            retrieved_documents=documents,
            retrieval_timestamp=time.time(),
            retrieval_method=retrieval_method,
            confidence_scores=confidence_scores or {},
            verification_status=verification_status,
            provenance_chain=[doc.doc_id for doc in documents]
        )
        
        self._records[record_id] = record
        
        self.logger.info(
            "provenance_record_created",
            record_id=record_id,
            document_count=len(documents),
            status=verification_status.name
        )
        
        return record
    
    def get_document_lineage(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Get document usage lineage.
        
        Args:
            doc_id: Document ID
            
        Returns:
            List of records using this document
        """
        lineage = []
        
        for record in self._records.values():
            if any(doc.doc_id == doc_id for doc in record.retrieved_documents):
                lineage.append(record.to_dict())
        
        return lineage
    
    def register_signature_validator(
        self,
        algorithm: str,
        validator: Callable[[SourceDocument], bool]
    ) -> None:
        """Register signature validation function."""
        self._validators[algorithm] = validator
    
    def export_provenance_report(self, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Export detailed provenance report.
        
        Args:
            record_id: Provenance record ID
            
        Returns:
            Detailed report or None
        """
        record = self._records.get(record_id)
        if not record:
            return None
        
        return {
            "record": record.to_dict(),
            "documents": [doc.to_dict() for doc in record.retrieved_documents],
            "verification_details": {
                doc.doc_id: self.verify_document(doc.doc_id).name
                for doc in record.retrieved_documents
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get provenance statistics."""
        return {
            "registered_documents": len(self._documents),
            "provenance_records": len(self._records),
            "verified_documents": sum(
                1 for doc in self._documents.values()
                if self.verify_document(doc.doc_id) == VerificationStatus.VERIFIED
            )
        }


class ProvenanceTracker:
    """
    Convenience wrapper for tracking provenance during RAG operations.
    """
    
    def __init__(self, provenance: RAGProvenance) -> None:
        """
        Initialize tracker.
        
        Args:
            provenance: RAGProvenance instance
        """
        self.provenance = provenance
        self.logger = structlog.get_logger("amcis.provenance_tracker")
    
    def track_retrieval(
        self,
        query: str,
        sources: List[Tuple[str, bytes]],
        method: str = "semantic_search"
    ) -> ProvenanceRecord:
        """
        Track document retrieval.
        
        Args:
            query: User query
            sources: List of (uri, content) tuples
            method: Retrieval method
            
        Returns:
            Provenance record
        """
        doc_ids = []
        
        for uri, content in sources:
            doc = self.provenance.register_document(uri, content)
            doc_ids.append(doc.doc_id)
        
        return self.provenance.create_provenance_record(
            query=query,
            document_ids=doc_ids,
            retrieval_method=method
        )
