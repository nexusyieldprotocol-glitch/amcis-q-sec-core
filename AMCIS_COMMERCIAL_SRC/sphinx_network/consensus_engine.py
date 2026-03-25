#!/usr/bin/env python3
"""
SPHINX™ HotStuff Consensus Engine
==================================
Implementation of the HotStuff Byzantine Fault Tolerant consensus protocol.

HotStuff provides:
- Linear communication complexity
- Responsive (communication depends on actual network delay)
- Streamlined leader replacement
- Chained consensus for pipelining

Commercial Version - Requires License
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict


logger = logging.getLogger("HotStuffConsensus")


class ConsensusPhase(Enum):
    """Phases of the HotStuff consensus protocol."""
    NEW_VIEW = auto()
    PREPARE = auto()
    PRE_COMMIT = auto()
    COMMIT = auto()
    DECIDE = auto()


@dataclass
class Proposal:
    """A proposal in the HotStuff protocol."""
    proposal_id: str
    view_number: int
    sequence_number: int
    proposer_id: str
    data: any
    timestamp: float
    parent_hash: Optional[str] = None
    signature: Optional[str] = None
    qc: Optional['QuorumCertificate'] = None


@dataclass
class Vote:
    """A vote on a proposal."""
    vote_id: str
    proposal_id: str
    view_number: int
    node_id: str
    decision: bool  # True = accept, False = reject
    timestamp: float
    signature: Optional[str] = None
    partial_sig: Optional[str] = None  # For threshold signatures


@dataclass
class QuorumCertificate:
    """A quorum certificate proving 2f+1 votes."""
    qc_id: str
    view_number: int
    proposal_id: str
    votes: List[Vote]
    voter_ids: List[str]
    aggregated_signature: Optional[str] = None
    timestamp: float = field(default_factory=lambda: __import__('time').time())


@dataclass
class ConsensusBlock:
    """A committed block in the chain."""
    block_id: str
    view_number: int
    sequence_number: int
    proposal: Proposal
    qc: QuorumCertificate
    commit_certificate: Optional[QuorumCertificate] = None
    parent_block_id: Optional[str] = None


class HotStuffConsensus:
    """
    HotStuff BFT Consensus Implementation
    
    Handles the full consensus lifecycle:
    1. Leader election (round-robin)
    2. Proposal creation and broadcast
    3. Vote collection and aggregation
    4. Quorum certificate formation
    5. Block commitment
    
    Args:
        node_id: This node's identifier
        public_key: Node's public key for verification
        total_nodes: Total nodes in the network (default 4)
        byzantine_threshold: Max Byzantine faults tolerated (default 1)
    """
    
    def __init__(
        self,
        node_id: str,
        public_key: str,
        total_nodes: int = 4,
        byzantine_threshold: int = 1
    ):
        self.node_id = node_id
        self.public_key = public_key
        self.total_nodes = total_nodes
        self.byzantine_threshold = byzantine_threshold
        self.quorum_size = 2 * byzantine_threshold + 1  # 2f+1
        
        # Consensus state
        self.view_number = 0
        self.sequence_number = 0
        self.phase = ConsensusPhase.NEW_VIEW
        
        # Current proposal
        self.current_proposal: Optional[Proposal] = None
        self.pending_votes: Dict[str, List[Vote]] = defaultdict(list)
        
        # Certificates
        self.high_qc: Optional[QuorumCertificate] = None
        self.locked_qc: Optional[QuorumCertificate] = None
        
        # Blockchain
        self.chain: List[ConsensusBlock] = []
        self.pending_blocks: Dict[str, ConsensusBlock] = {}
        
        # Leader tracking
        self.current_leader: Optional[str] = None
        self.leader_rotation: List[str] = []
        
        # View change
        self.view_change_votes: Dict[int, List[Vote]] = defaultdict(list)
        self.timeout_cert: Optional[QuorumCertificate] = None
        
        self._running = False
        
        logger.info(f"HotStuff consensus initialized for {node_id}")
    
    def start(self) -> None:
        """Start the consensus engine."""
        self._running = True
        logger.info("HotStuff consensus started")
    
    def stop(self) -> None:
        """Stop the consensus engine."""
        self._running = False
        logger.info("HotStuff consensus stopped")
    
    async def tick(self) -> None:
        """Process one consensus tick."""
        if not self._running:
            return
        
        # Check for proposal timeout
        if self.phase == ConsensusPhase.PREPARE and self.current_proposal:
            if self._is_proposal_timeout():
                await self._initiate_view_change()
        
        # Check for view change timeout
        if self.phase == ConsensusPhase.NEW_VIEW:
            if self._is_view_change_timeout():
                await self._process_view_change()
    
    def create_proposal(self, data: any, view_number: int) -> Proposal:
        """
        Create a new proposal as the leader.
        
        Args:
            data: The data to propose
            view_number: Current view number
            
        Returns:
            New Proposal
        """
        parent_hash = None
        if self.chain:
            parent_hash = self.chain[-1].block_id
        
        proposal = Proposal(
            proposal_id=f"prop-{view_number}-{self.sequence_number}",
            view_number=view_number,
            sequence_number=self.sequence_number,
            proposer_id=self.node_id,
            data=data,
            timestamp=__import__('time').time(),
            parent_hash=parent_hash,
            qc=self.high_qc
        )
        
        self.current_proposal = proposal
        self.phase = ConsensusPhase.PREPARE
        
        logger.info(f"Created proposal {proposal.proposal_id} for view {view_number}")
        return proposal
    
    def create_vote(self, proposal: Proposal, node_id: str) -> Vote:
        """
        Create a vote on a proposal.
        
        Args:
            proposal: The proposal to vote on
            node_id: This node's ID
            
        Returns:
            New Vote
        """
        # Validate proposal
        if not self._validate_proposal(proposal):
            return Vote(
                vote_id=f"vote-{proposal.proposal_id}-{node_id}",
                proposal_id=proposal.proposal_id,
                view_number=proposal.view_number,
                node_id=node_id,
                decision=False,
                timestamp=__import__('time').time()
            )
        
        vote = Vote(
            vote_id=f"vote-{proposal.proposal_id}-{node_id}",
            proposal_id=proposal.proposal_id,
            view_number=proposal.view_number,
            node_id=node_id,
            decision=True,
            timestamp=__import__('time').time()
        )
        
        return vote
    
    def process_vote(self, vote: Vote) -> Optional[QuorumCertificate]:
        """
        Process an incoming vote.
        
        Args:
            vote: The vote to process
            
        Returns:
            QuorumCertificate if quorum reached, None otherwise
        """
        if vote.proposal_id not in self.pending_votes:
            self.pending_votes[vote.proposal_id] = []
        
        # Check for duplicate vote from same node
        existing_votes = self.pending_votes[vote.proposal_id]
        if any(v.node_id == vote.node_id for v in existing_votes):
            logger.warning(f"Duplicate vote from {vote.node_id}")
            return None
        
        self.pending_votes[vote.proposal_id].append(vote)
        
        # Check if we have a quorum
        votes = self.pending_votes[vote.proposal_id]
        accept_votes = [v for v in votes if v.decision]
        
        if len(accept_votes) >= self.quorum_size:
            # Create quorum certificate
            qc = QuorumCertificate(
                qc_id=f"qc-{vote.proposal_id}",
                view_number=vote.view_number,
                proposal_id=vote.proposal_id,
                votes=accept_votes,
                voter_ids=[v.node_id for v in accept_votes]
            )
            
            self.high_qc = qc
            
            logger.info(f"Quorum reached for {vote.proposal_id} with {len(accept_votes)} votes")
            return qc
        
        return None
    
    def process_qc(self, qc: QuorumCertificate) -> bool:
        """
        Process a quorum certificate.
        
        Args:
            qc: The quorum certificate
            
        Returns:
            True if block committed
        """
        if qc.view_number > self.view_number:
            self.high_qc = qc
            self.view_number = qc.view_number
            
            # Create committed block
            if self.current_proposal and self.current_proposal.proposal_id == qc.proposal_id:
                block = ConsensusBlock(
                    block_id=f"block-{qc.view_number}-{self.sequence_number}",
                    view_number=qc.view_number,
                    sequence_number=self.sequence_number,
                    proposal=self.current_proposal,
                    qc=qc,
                    parent_block_id=self.chain[-1].block_id if self.chain else None
                )
                
                self.chain.append(block)
                self.sequence_number += 1
                self.phase = ConsensusPhase.DECIDE
                
                logger.info(f"Block committed: {block.block_id}")
                return True
        
        return False
    
    def get_qc_for_proposal(self, proposal_id: str) -> Optional[QuorumCertificate]:
        """Get the quorum certificate for a proposal if it exists."""
        if self.high_qc and self.high_qc.proposal_id == proposal_id:
            return self.high_qc
        return None
    
    def get_leader_for_view(self, view_number: int, nodes: List[str]) -> str:
        """
        Determine leader for a view using round-robin rotation.
        
        Args:
            view_number: The view number
            nodes: List of node IDs
            
        Returns:
            Leader node ID
        """
        if not nodes:
            return self.node_id
        return nodes[view_number % len(nodes)]
    
    async def _initiate_view_change(self) -> None:
        """Initiate a view change due to timeout."""
        logger.warning(f"View {self.view_number} timeout, initiating view change")
        
        self.phase = ConsensusPhase.NEW_VIEW
        self.view_number += 1
        self.current_proposal = None
        self.pending_votes.clear()
    
    async def _process_view_change(self) -> None:
        """Process pending view change votes."""
        # Check if we have enough view change votes
        vc_votes = self.view_change_votes.get(self.view_number, [])
        
        if len(vc_votes) >= self.quorum_size:
            # Create timeout certificate
            self.timeout_cert = QuorumCertificate(
                qc_id=f"tc-{self.view_number}",
                view_number=self.view_number,
                proposal_id="view_change",
                votes=vc_votes,
                voter_ids=[v.node_id for v in vc_votes]
            )
            
            logger.info(f"View change to {self.view_number} certified")
    
    def _validate_proposal(self, proposal: Proposal) -> bool:
        """Validate a proposal according to HotStuff rules."""
        # Check view number
        if proposal.view_number < self.view_number:
            logger.debug(f"Proposal view {proposal.view_number} < current {self.view_number}")
            return False
        
        # Check locked QC
        if self.locked_qc and proposal.qc:
            if proposal.qc.view_number < self.locked_qc.view_number:
                logger.debug("Proposal QC older than locked QC")
                return False
        
        return True
    
    def _is_proposal_timeout(self) -> bool:
        """Check if current proposal has timed out."""
        # 5 second timeout for proposals
        if self.current_proposal:
            elapsed = __import__('time').time() - self.current_proposal.timestamp
            return elapsed > 5.0
        return False
    
    def _is_view_change_timeout(self) -> bool:
        """Check if view change has timed out."""
        # 3 second timeout for view changes
        return False  # Placeholder
    
    def get_chain_height(self) -> int:
        """Get the current blockchain height."""
        return len(self.chain)
    
    def get_latest_block(self) -> Optional[ConsensusBlock]:
        """Get the latest committed block."""
        if self.chain:
            return self.chain[-1]
        return None
    
    def get_status(self) -> Dict:
        """Get consensus engine status."""
        return {
            "view_number": self.view_number,
            "sequence_number": self.sequence_number,
            "phase": self.phase.name,
            "chain_height": len(self.chain),
            "quorum_size": self.quorum_size,
            "has_high_qc": self.high_qc is not None,
            "has_locked_qc": self.locked_qc is not None,
            "current_proposal": self.current_proposal.proposal_id if self.current_proposal else None,
            "pending_votes": {k: len(v) for k, v in self.pending_votes.items()}
        }
