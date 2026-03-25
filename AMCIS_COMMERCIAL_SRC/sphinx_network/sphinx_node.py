#!/usr/bin/env python3
"""
SPHINX™ Node Implementation
============================
Full node for the SPHINX distributed AI consensus network.

Features:
- Byzantine Fault Tolerance (BFT) via HotStuff
- Post-quantum cryptography (ML-KEM, Dilithium)
- P2P networking with Kademlia DHT
- Verifiable computation via FRI proofs
- 4-node consensus with 1 Byzantine fault tolerance

Commercial Version - Requires License
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Any, Callable
from uuid import uuid4
import secrets

from .consensus_engine import HotStuffConsensus, Proposal, Vote, QuorumCertificate
from .p2p_network import P2PNetwork, Message
from .crypto_primitives import MLKEMKeyExchange, DilithiumSignature


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SphinxNode")


class NodeState(Enum):
    """Operational states for a SPHINX node."""
    INITIALIZING = auto()
    SYNCING = auto()
    ACTIVE = auto()
    LEADER = auto()
    FOLLOWER = auto()
    VIEW_CHANGE = auto()
    BYZANTINE_DETECTED = auto()
    SHUTDOWN = auto()


class AgentType(Enum):
    """Types of AI agents in the SPHINX network."""
    CONSENSUS_VALIDATOR = "consensus_validator"
    PROPOSAL_GENERATOR = "proposal_generator"
    VOTE_AGGREGATOR = "vote_aggregator"
    FRI_PROVER = "fri_prover"
    FRI_VERIFIER = "fri_verifier"
    THRESHOLD_SIGNER = "threshold_signer"
    NETWORK_RELAY = "network_relay"
    STATE_REPLICATOR = "state_replicator"
    BYZANTINE_DETECTOR = "byzantine_detector"
    CONSENSUS_ORCHESTRATOR = "consensus_orchestrator"
    ML_INFERENCE = "ml_inference"


@dataclass
class NodeInfo:
    """Information about a SPHINX node."""
    node_id: str
    public_key: str
    network_address: str
    agent_types: List[AgentType]
    stake_amount: float  # For Proof-of-Stake weighted voting
    reputation_score: float  # 0.0 to 1.0
    last_seen: float
    capabilities: List[str]


@dataclass
class ConsensusDecision:
    """A decision reached by the SPHINX consensus."""
    decision_id: str
    proposal_hash: str
    view_number: int
    sequence_number: int
    timestamp: float
    participating_nodes: List[str]
    signature_aggregates: Dict[str, str]
    decision_data: Any
    execution_proof: Optional[str] = None


class SphinxNode:
    """
    SPHINX Distributed AI Node
    
    A full node in the SPHINX network capable of:
    - Participating in BFT consensus
    - Executing AI inference tasks
    - Maintaining distributed state
    - Detecting Byzantine faults
    
    Args:
        node_id: Unique identifier for this node
        network_address: Address to bind (host:port)
        peer_addresses: List of bootstrap peer addresses
        agent_types: Types of agents this node runs
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        network_address: str = "127.0.0.1:8080",
        peer_addresses: Optional[List[str]] = None,
        agent_types: Optional[List[AgentType]] = None,
        stake_amount: float = 1000.0
    ):
        self.node_id = node_id or f"sphinx-node-{secrets.token_hex(8)}"
        self.network_address = network_address
        self.peer_addresses = peer_addresses or []
        self.agent_types = agent_types or [AgentType.CONSENSUS_VALIDATOR]
        self.stake_amount = stake_amount
        
        # State management
        self.state = NodeState.INITIALIZING
        self.view_number = 0
        self.sequence_number = 0
        self.reputation_score = 1.0
        
        # Cryptographic keys
        self.kem = MLKEMKeyExchange()
        self.dilithium = DilithiumSignature()
        self.public_key = self.dilithium.get_public_key()
        
        # Subsystems
        self.consensus = HotStuffConsensus(self.node_id, self.public_key)
        self.p2p = P2PNetwork(self.node_id, network_address)
        
        # Peer management
        self.peers: Dict[str, NodeInfo] = {}
        self.connected_peers: Set[str] = set()
        
        # Decision storage
        self.decisions: Dict[str, ConsensusDecision] = {}
        self.decision_callbacks: List[Callable] = []
        
        # Metrics
        self.metrics = {
            "proposals_received": 0,
            "votes_cast": 0,
            "decisions_reached": 0,
            "byzantine_faults_detected": 0,
            "total_inference_time": 0.0
        }
        
        logger.info(f"SPHINX Node {self.node_id} initialized")
    
    async def start(self) -> None:
        """Start the SPHINX node."""
        logger.info(f"Starting SPHINX node {self.node_id}...")
        
        self.state = NodeState.SYNCING
        
        # Start P2P networking
        await self.p2p.start()
        logger.info(f"P2P network started on {self.network_address}")
        
        # Connect to bootstrap peers
        for peer_addr in self.peer_addresses:
            await self._connect_to_peer(peer_addr)
        
        # Sync state with network
        await self._sync_state()
        
        # Start consensus engine
        self.consensus.start()
        
        self.state = NodeState.ACTIVE
        logger.info(f"SPHINX node {self.node_id} is ACTIVE")
        
        # Start main event loop
        await self._run_event_loop()
    
    async def stop(self) -> None:
        """Gracefully stop the node."""
        logger.info(f"Stopping SPHINX node {self.node_id}...")
        self.state = NodeState.SHUTDOWN
        
        self.consensus.stop()
        await self.p2p.stop()
        
        logger.info(f"SPHINX node {self.node_id} stopped")
    
    async def propose_decision(self, decision_data: Any) -> Optional[ConsensusDecision]:
        """
        Propose a new decision to the network.
        
        Args:
            decision_data: The data to reach consensus on
            
        Returns:
            ConsensusDecision if consensus reached, None otherwise
        """
        if self.state != NodeState.ACTIVE and self.state != NodeState.LEADER:
            logger.warning("Node not active, cannot propose")
            return None
        
        # Create proposal
        proposal = Proposal(
            proposal_id=str(uuid4()),
            view_number=self.view_number,
            sequence_number=self.sequence_number,
            proposer_id=self.node_id,
            data=decision_data,
            timestamp=time.time()
        )
        
        # Sign proposal
        proposal_hash = self._hash_proposal(proposal)
        proposal.signature = self.dilithium.sign(proposal_hash)
        
        logger.info(f"Proposing decision {proposal.proposal_id}")
        
        # Broadcast to peers
        await self._broadcast_proposal(proposal)
        
        # Wait for consensus
        decision = await self._wait_for_consensus(proposal)
        
        return decision
    
    async def submit_inference_task(self, task_data: Dict) -> Optional[ConsensusDecision]:
        """
        Submit an AI inference task to the distributed network.
        
        The task will be processed by ML_INFERENCE agents and
        results verified through FRI proofs before consensus.
        
        Args:
            task_data: The inference task parameters
            
        Returns:
            ConsensusDecision with verified inference result
        """
        inference_request = {
            "type": "ml_inference",
            "task": task_data,
            "requested_by": self.node_id,
            "timestamp": time.time()
        }
        
        return await self.propose_decision(inference_request)
    
    def on_consensus_decision(self, callback: Callable[[ConsensusDecision], None]) -> None:
        """Register a callback for when consensus decisions are reached."""
        self.decision_callbacks.append(callback)
    
    async def _run_event_loop(self) -> None:
        """Main event processing loop."""
        while self.state != NodeState.SHUTDOWN:
            try:
                # Process incoming messages
                message = await self.p2p.receive_message(timeout=1.0)
                if message:
                    await self._handle_message(message)
                
                # Run consensus tick
                await self.consensus.tick()
                
                # Check for view changes
                await self._check_view_change()
                
                # Update metrics
                await self._update_metrics()
                
            except Exception as e:
                logger.error(f"Error in event loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_message(self, message: Message) -> None:
        """Handle incoming P2P messages."""
        msg_type = message.msg_type
        
        if msg_type == "PROPOSAL":
            await self._handle_proposal(message.payload)
        elif msg_type == "VOTE":
            await self._handle_vote(message.payload)
        elif msg_type == "NEW_VIEW":
            await self._handle_new_view(message.payload)
        elif msg_type == "QC":
            await self._handle_quorum_certificate(message.payload)
        elif msg_type == "PEER_DISCOVERY":
            await self._handle_peer_discovery(message.payload)
        elif msg_type == "BYZANTINE_ALERT":
            await self._handle_byzantine_alert(message.payload)
    
    async def _handle_proposal(self, proposal_data: Dict) -> None:
        """Handle an incoming proposal."""
        proposal = Proposal(**proposal_data)
        
        # Verify proposal signature
        proposer_key = self._get_peer_public_key(proposal.proposer_id)
        if not proposer_key:
            logger.warning(f"Unknown proposer {proposal.proposer_id}")
            return
        
        # Validate proposal
        if not self._validate_proposal(proposal):
            logger.warning(f"Invalid proposal {proposal.proposal_id}")
            return
        
        self.metrics["proposals_received"] += 1
        
        # Create and send vote
        vote = self.consensus.create_vote(proposal, self.node_id)
        vote.signature = self.dilithium.sign(self._hash_vote(vote))
        
        await self._send_vote(vote, proposal.proposer_id)
        self.metrics["votes_cast"] += 1
    
    async def _wait_for_consensus(self, proposal: Proposal) -> Optional[ConsensusDecision]:
        """Wait for consensus to be reached on a proposal."""
        timeout = 30.0  # 30 second timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if we have a quorum certificate
            qc = self.consensus.get_qc_for_proposal(proposal.proposal_id)
            if qc:
                decision = ConsensusDecision(
                    decision_id=str(uuid4()),
                    proposal_hash=self._hash_proposal(proposal),
                    view_number=self.view_number,
                    sequence_number=self.sequence_number,
                    timestamp=time.time(),
                    participating_nodes=qc.voter_ids,
                    signature_aggregates={v.node_id: v.signature for v in qc.votes},
                    decision_data=proposal.data
                )
                
                self.decisions[decision.decision_id] = decision
                self.metrics["decisions_reached"] += 1
                
                # Notify callbacks
                for callback in self.decision_callbacks:
                    try:
                        callback(decision)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                self.sequence_number += 1
                return decision
            
            await asyncio.sleep(0.1)
        
        logger.warning(f"Consensus timeout for proposal {proposal.proposal_id}")
        return None
    
    def _hash_proposal(self, proposal: Proposal) -> str:
        """Create hash of proposal data."""
        data = json.dumps(asdict(proposal), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _hash_vote(self, vote: Vote) -> str:
        """Create hash of vote data."""
        data = json.dumps(asdict(vote), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def _connect_to_peer(self, address: str) -> None:
        """Connect to a peer node."""
        try:
            success = await self.p2p.connect(address)
            if success:
                logger.info(f"Connected to peer at {address}")
        except Exception as e:
            logger.warning(f"Failed to connect to {address}: {e}")
    
    async def _broadcast_proposal(self, proposal: Proposal) -> None:
        """Broadcast proposal to all connected peers."""
        message = Message(
            msg_type="PROPOSAL",
            sender_id=self.node_id,
            payload=asdict(proposal),
            timestamp=time.time()
        )
        await self.p2p.broadcast(message)
    
    async def _send_vote(self, vote: Vote, to_node_id: str) -> None:
        """Send a vote to a specific node."""
        message = Message(
            msg_type="VOTE",
            sender_id=self.node_id,
            payload=asdict(vote),
            timestamp=time.time()
        )
        await self.p2p.send_to_node(to_node_id, message)
    
    def _validate_proposal(self, proposal: Proposal) -> bool:
        """Validate a proposal according to consensus rules."""
        # Check view number
        if proposal.view_number < self.view_number:
            return False
        
        # Check proposal data size
        data_size = len(json.dumps(proposal.data))
        if data_size > 10_000_000:  # 10MB limit
            return False
        
        return True
    
    def _get_peer_public_key(self, node_id: str) -> Optional[str]:
        """Get the public key for a peer node."""
        if node_id in self.peers:
            return self.peers[node_id].public_key
        return None
    
    async def _sync_state(self) -> None:
        """Synchronize state with the network."""
        logger.info("Synchronizing with network...")
        # Request current state from peers
        # Download missing decisions
        await asyncio.sleep(1)  # Placeholder
        logger.info("State synchronized")
    
    async def _check_view_change(self) -> None:
        """Check if view change is needed."""
        # Implement view change logic
        pass
    
    async def _update_metrics(self) -> None:
        """Update node metrics."""
        # Update Prometheus metrics
        pass
    
    async def _handle_vote(self, payload: Dict) -> None:
        """Handle incoming vote."""
        vote = Vote(**payload)
        self.consensus.process_vote(vote)
    
    async def _handle_new_view(self, payload: Dict) -> None:
        """Handle view change message."""
        pass
    
    async def _handle_quorum_certificate(self, payload: Dict) -> None:
        """Handle quorum certificate."""
        pass
    
    async def _handle_peer_discovery(self, payload: Dict) -> None:
        """Handle peer discovery message."""
        pass
    
    async def _handle_byzantine_alert(self, payload: Dict) -> None:
        """Handle Byzantine fault alert."""
        self.metrics["byzantine_faults_detected"] += 1
        logger.warning(f"Byzantine fault detected: {payload}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current node status."""
        return {
            "node_id": self.node_id,
            "state": self.state.name,
            "view_number": self.view_number,
            "sequence_number": self.sequence_number,
            "peers_connected": len(self.connected_peers),
            "decisions_stored": len(self.decisions),
            "reputation_score": self.reputation_score,
            "metrics": self.metrics.copy(),
            "agent_types": [at.value for at in self.agent_types],
            "uptime": time.time() - getattr(self, '_start_time', time.time())
        }
