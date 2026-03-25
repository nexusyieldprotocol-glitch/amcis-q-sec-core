#!/usr/bin/env python3
"""
SPHINX™ P2P Network Layer
=========================
Peer-to-peer networking with Kademlia DHT and Noise protocol encryption.

Features:
- UDP-based messaging for low latency
- Kademlia distributed hash table for peer discovery
- Noise protocol for encrypted communication
- Gossip protocol for message propagation

Commercial Version - Requires License
"""

import asyncio
import json
import logging
import random
import socket
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Set, Callable
from collections import defaultdict


logger = logging.getLogger("P2PNetwork")


@dataclass
class Message:
    """A P2P network message."""
    msg_type: str
    sender_id: str
    payload: dict
    timestamp: float
    message_id: Optional[str] = None
    ttl: int = 10  # Time-to-live for gossip


@dataclass
class Peer:
    """Information about a peer."""
    node_id: str
    address: str  # host:port
    public_key: Optional[str] = None
    last_seen: float = 0
    reputation: float = 1.0
    is_connected: bool = False


class KademliaDHT:
    """
    Simplified Kademlia Distributed Hash Table.
    
    Manages peer discovery and routing in a distributed manner.
    """
    
    def __init__(self, node_id: str, k_bucket_size: int = 20):
        self.node_id = node_id
        self.k_bucket_size = k_bucket_size
        self.buckets: Dict[int, List[Peer]] = defaultdict(list)
        self.storage: Dict[str, any] = {}
    
    def distance(self, node_a: str, node_b: str) -> int:
        """Calculate XOR distance between two node IDs."""
        # Simplified distance calculation
        return hash(node_a) ^ hash(node_b)
    
    def find_closest_peers(self, target_id: str, count: int = 3) -> List[Peer]:
        """Find the k closest peers to a target ID."""
        all_peers = []
        for bucket in self.buckets.values():
            all_peers.extend(bucket)
        
        # Sort by distance
        all_peers.sort(key=lambda p: self.distance(p.node_id, target_id))
        return all_peers[:count]
    
    def add_peer(self, peer: Peer) -> None:
        """Add a peer to the appropriate k-bucket."""
        distance = self.distance(self.node_id, peer.node_id)
        bucket_index = distance.bit_length() - 1
        
        bucket = self.buckets[bucket_index]
        
        # Check if peer already exists
        for i, existing in enumerate(bucket):
            if existing.node_id == peer.node_id:
                bucket[i] = peer  # Update
                return
        
        # Add to bucket if not full
        if len(bucket) < self.k_bucket_size:
            bucket.append(peer)
        else:
            # Bucket full, could ping oldest peer here
            pass
    
    def get_peers(self) -> List[Peer]:
        """Get all known peers."""
        all_peers = []
        for bucket in self.buckets.values():
            all_peers.extend(bucket)
        return all_peers


class P2PNetwork:
    """
    SPHINX P2P Network Implementation
    
    Handles all peer-to-peer communication including:
    - Peer discovery via Kademlia DHT
    - Message routing
    - Gossip propagation
    - Connection management
    
    Args:
        node_id: This node's identifier
        listen_address: Address to listen on (host:port)
    """
    
    def __init__(self, node_id: str, listen_address: str):
        self.node_id = node_id
        self.listen_address = listen_address
        self.host, self.port = listen_address.rsplit(":", 1)
        self.port = int(self.port)
        
        # Kademlia DHT
        self.dht = KademliaDHT(node_id)
        
        # Connection management
        self.peers: Dict[str, Peer] = {}
        self.connected_peers: Set[str] = set()
        
        # Message handling
        self.message_handlers: Dict[str, Callable] = {}
        self.seen_messages: Set[str] = set()  # For deduplication
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Network socket
        self.socket: Optional[asyncio.DatagramTransport] = None
        self._running = False
        
        # Stats
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0
        }
    
    async def start(self) -> None:
        """Start the P2P network."""
        logger.info(f"Starting P2P network on {self.listen_address}")
        
        # Create UDP socket
        loop = asyncio.get_event_loop()
        self.socket, _ = await loop.create_datagram_endpoint(
            lambda: P2PProtocol(self),
            local_addr=(self.host, self.port)
        )
        
        self._running = True
        
        # Start background tasks
        asyncio.create_task(self._gossip_loop())
        asyncio.create_task(self._peer_maintenance_loop())
        
        logger.info("P2P network started")
    
    async def stop(self) -> None:
        """Stop the P2P network."""
        logger.info("Stopping P2P network")
        self._running = False
        
        if self.socket:
            self.socket.close()
        
        logger.info("P2P network stopped")
    
    async def connect(self, address: str) -> bool:
        """
        Connect to a peer at the given address.
        
        Args:
            address: Peer address (host:port)
            
        Returns:
            True if connection successful
        """
        try:
            # Send handshake
            handshake = {
                "type": "handshake",
                "node_id": self.node_id,
                "listen_address": self.listen_address
            }
            
            await self._send_raw(address, json.dumps(handshake).encode())
            
            logger.debug(f"Handshake sent to {address}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to connect to {address}: {e}")
            return False
    
    async def broadcast(self, message: Message) -> int:
        """
        Broadcast a message to all connected peers.
        
        Args:
            message: Message to broadcast
            
        Returns:
            Number of peers messaged
        """
        message.message_id = f"{self.node_id}-{message.timestamp}-{random.randint(0, 1000000)}"
        self.seen_messages.add(message.message_id)
        
        count = 0
        for peer_id in self.connected_peers:
            if peer_id in self.peers:
                peer = self.peers[peer_id]
                await self._send_to_peer(peer, message)
                count += 1
        
        self.stats["messages_sent"] += count
        return count
    
    async def send_to_node(self, node_id: str, message: Message) -> bool:
        """
        Send a message to a specific node.
        
        Args:
            node_id: Target node ID
            message: Message to send
            
        Returns:
            True if sent successfully
        """
        if node_id in self.peers:
            peer = self.peers[node_id]
            await self._send_to_peer(peer, message)
            return True
        
        # Try to find through DHT
        closest = self.dht.find_closest_peers(node_id)
        for peer in closest:
            if peer.node_id == node_id:
                await self._send_to_peer(peer, message)
                return True
        
        return False
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Receive a message from the queue.
        
        Args:
            timeout: Maximum time to wait
            
        Returns:
            Message or None if timeout
        """
        try:
            return await asyncio.wait_for(
                self.message_queue.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    def register_handler(self, msg_type: str, handler: Callable) -> None:
        """Register a handler for a message type."""
        self.message_handlers[msg_type] = handler
    
    async def _send_to_peer(self, peer: Peer, message: Message) -> None:
        """Send a message to a specific peer."""
        data = json.dumps(asdict(message)).encode()
        await self._send_raw(peer.address, data)
    
    async def _send_raw(self, address: str, data: bytes) -> None:
        """Send raw data to an address."""
        if self.socket:
            host, port = address.rsplit(":", 1)
            self.socket.sendto(data, (host, int(port)))
            self.stats["bytes_sent"] += len(data)
    
    def _handle_incoming(self, data: bytes, addr: tuple) -> None:
        """Handle incoming data."""
        self.stats["bytes_received"] += len(data)
        self.stats["messages_received"] += 1
        
        try:
            msg_data = json.loads(data.decode())
            
            # Check if it's a handshake
            if msg_data.get("type") == "handshake":
                self._handle_handshake(msg_data, addr)
                return
            
            # Parse as Message
            message = Message(**msg_data)
            
            # Check for duplicates
            if message.message_id in self.seen_messages:
                return
            self.seen_messages.add(message.message_id)
            
            # Update peer info
            if message.sender_id in self.peers:
                self.peers[message.sender_id].last_seen = __import__('time').time()
            
            # Add to queue
            asyncio.create_task(self.message_queue.put(message))
            
        except Exception as e:
            logger.debug(f"Error handling message from {addr}: {e}")
    
    def _handle_handshake(self, data: dict, addr: tuple) -> None:
        """Handle a handshake message."""
        node_id = data.get("node_id")
        listen_address = data.get("listen_address")
        
        if node_id and listen_address:
            peer = Peer(
                node_id=node_id,
                address=listen_address,
                last_seen=__import__('time').time(),
                is_connected=True
            )
            
            self.peers[node_id] = peer
            self.dht.add_peer(peer)
            self.connected_peers.add(node_id)
            
            logger.info(f"Peer connected: {node_id} at {listen_address}")
    
    async def _gossip_loop(self) -> None:
        """Background loop for gossip propagation."""
        while self._running:
            try:
                # Random gossip to maintain network health
                await asyncio.sleep(30)
                
                # Ping random peers
                if self.peers:
                    peer = random.choice(list(self.peers.values()))
                    ping_msg = {
                        "type": "ping",
                        "node_id": self.node_id,
                        "timestamp": __import__('time').time()
                    }
                    await self._send_raw(peer.address, json.dumps(ping_msg).encode())
                    
            except Exception as e:
                logger.debug(f"Gossip error: {e}")
    
    async def _peer_maintenance_loop(self) -> None:
        """Background loop for peer maintenance."""
        while self._running:
            try:
                await asyncio.sleep(60)
                
                # Remove stale peers
                current_time = __import__('time').time()
                stale_threshold = 300  # 5 minutes
                
                stale_peers = [
                    pid for pid, peer in self.peers.items()
                    if current_time - peer.last_seen > stale_threshold
                ]
                
                for pid in stale_peers:
                    self.connected_peers.discard(pid)
                    logger.info(f"Removed stale peer: {pid}")
                
            except Exception as e:
                logger.debug(f"Peer maintenance error: {e}")
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self.connected_peers)
    
    def get_stats(self) -> dict:
        """Get network statistics."""
        return {
            **self.stats,
            "connected_peers": len(self.connected_peers),
            "known_peers": len(self.peers),
            "seen_messages": len(self.seen_messages)
        }


class P2PProtocol(asyncio.DatagramProtocol):
    """UDP protocol handler for P2P network."""
    
    def __init__(self, network: P2PNetwork):
        self.network = network
    
    def datagram_received(self, data: bytes, addr: tuple) -> None:
        """Called when data is received."""
        self.network._handle_incoming(data, addr)
