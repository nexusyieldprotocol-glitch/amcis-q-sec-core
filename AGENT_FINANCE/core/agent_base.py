"""
AMCIS Financial AI Agent Core Framework
Base classes for autonomous revenue-generating agents
"""

import asyncio
import uuid
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from enum import Enum
import hashlib
import time

logger = logging.getLogger(__name__)


class AgentState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AgentPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentMessage:
    """Inter-agent communication protocol"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    recipient_id: Optional[str] = None  # None = broadcast
    message_type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: AgentPriority = AgentPriority.NORMAL
    ttl: int = 300  # Time to live in seconds
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "message_type": self.message_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "ttl": self.ttl
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AgentMessage':
        msg = cls(
            id=data["id"],
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            message_type=data["message_type"],
            payload=data.get("payload", {}),
            timestamp=data["timestamp"],
            priority=AgentPriority(data.get("priority", 2)),
            ttl=data.get("ttl", 300)
        )
        return msg


@dataclass
class AgentMetrics:
    """Revenue and performance tracking"""
    agent_id: str = ""
    total_revenue: float = 0.0
    total_costs: float = 0.0
    profit: float = 0.0
    trades_executed: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    uptime_seconds: float = 0.0
    last_update: float = field(default_factory=time.time)
    
    def update_profit(self, revenue: float, costs: float):
        self.total_revenue += revenue
        self.total_costs += costs
        self.profit = self.total_revenue - self.total_costs
        self.last_update = time.time()
    
    def record_trade(self, success: bool):
        self.trades_executed += 1
        if success:
            self.successful_trades += 1
        else:
            self.failed_trades += 1
    
    @property
    def win_rate(self) -> float:
        if self.trades_executed == 0:
            return 0.0
        return self.successful_trades / self.trades_executed
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "total_revenue": self.total_revenue,
            "total_costs": self.total_costs,
            "profit": self.profit,
            "trades_executed": self.trades_executed,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "win_rate": self.win_rate,
            "uptime_seconds": self.uptime_seconds,
            "last_update": self.last_update
        }


class MessageBus:
    """High-throughput message broker for agent swarms"""
    
    def __init__(self, max_queue_size: int = 10000):
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.message_history: List[AgentMessage] = []
        self.max_history = 1000
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start message processing loop"""
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("MessageBus started")
        
    async def stop(self):
        """Stop message processing"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("MessageBus stopped")
        
    async def _process_loop(self):
        """Main message distribution loop"""
        while self._running:
            try:
                message: AgentMessage = await asyncio.wait_for(
                    self.message_queue.get(), timeout=1.0
                )
                await self._distribute(message)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                
    async def _distribute(self, message: AgentMessage):
        """Distribute message to subscribers"""
        # Check TTL
        if time.time() - message.timestamp > message.ttl:
            return
            
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
            
        # Distribute to subscribers
        handlers = self.subscribers.get(message.message_type, [])
        
        # Also distribute to broadcast subscribers
        if message.recipient_id is None:
            handlers.extend(self.subscribers.get("*", []))
            
        if handlers:
            await asyncio.gather(
                *[handler(message) for handler in handlers],
                return_exceptions=True
            )
            
    def subscribe(self, message_type: str, handler: Callable):
        """Subscribe to message type"""
        if message_type not in self.subscribers:
            self.subscribers[message_type] = []
        self.subscribers[message_type].append(handler)
        
    def unsubscribe(self, message_type: str, handler: Callable):
        """Unsubscribe from message type"""
        if message_type in self.subscribers:
            if handler in self.subscribers[message_type]:
                self.subscribers[message_type].remove(handler)
                
    async def publish(self, message: AgentMessage):
        """Publish message to bus"""
        try:
            self.message_queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("Message bus queue full, dropping message")
            
    def get_history(self, message_type: Optional[str] = None, 
                    limit: int = 100) -> List[AgentMessage]:
        """Get message history"""
        messages = self.message_history
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]
        return messages[-limit:]


class BaseAgent(ABC):
    """
    Base class for all revenue-generating financial agents
    """
    
    def __init__(self, name: str, agent_type: str, message_bus: MessageBus,
                 config: Optional[Dict] = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.agent_type = agent_type
        self.message_bus = message_bus
        self.config = config or {}
        
        self.state = AgentState.IDLE
        self.metrics = AgentMetrics(agent_id=self.id)
        self._task: Optional[asyncio.Task] = None
        self._start_time: Optional[float] = None
        self._message_handlers: Dict[str, Callable] = {}
        
        # Performance tuning
        self.loop_interval = self.config.get("loop_interval", 1.0)
        self.max_concurrent_operations = self.config.get("max_concurrent", 5)
        self._semaphore = asyncio.Semaphore(self.max_concurrent_operations)
        
    async def initialize(self):
        """Initialize agent resources"""
        self._register_handlers()
        await self._setup()
        logger.info(f"Agent {self.name} ({self.id}) initialized")
        
    async def _setup(self):
        """Override for custom setup"""
        pass
        
    def _register_handlers(self):
        """Register message handlers"""
        for msg_type, handler in self._message_handlers.items():
            self.message_bus.subscribe(msg_type, self._wrap_handler(handler))
            
    def _wrap_handler(self, handler: Callable) -> Callable:
        """Wrap handler with error handling"""
        async def wrapper(message: AgentMessage):
            try:
                if message.recipient_id and message.recipient_id != self.id:
                    return
                await handler(message)
            except Exception as e:
                logger.error(f"Handler error in {self.name}: {e}")
                await self._handle_error(e)
        return wrapper
        
    async def start(self):
        """Start agent operation"""
        if self.state == AgentState.RUNNING:
            return
            
        self.state = AgentState.RUNNING
        self._start_time = time.time()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Agent {self.name} started")
        
    async def stop(self):
        """Stop agent operation"""
        self.state = AgentState.STOPPED
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        # Update final metrics
        if self._start_time:
            self.metrics.uptime_seconds += time.time() - self._start_time
            
        logger.info(f"Agent {self.name} stopped. Final profit: ${self.metrics.profit:.2f}")
        
    async def pause(self):
        """Pause agent temporarily"""
        self.state = AgentState.PAUSED
        logger.info(f"Agent {self.name} paused")
        
    async def resume(self):
        """Resume agent operation"""
        self.state = AgentState.RUNNING
        logger.info(f"Agent {self.name} resumed")
        
    async def _run_loop(self):
        """Main agent execution loop"""
        while self.state != AgentState.STOPPED:
            try:
                if self.state == AgentState.RUNNING:
                    async with self._semaphore:
                        await self.execute_cycle()
                        
                await asyncio.sleep(self.loop_interval)
                
            except Exception as e:
                logger.error(f"Agent {self.name} cycle error: {e}")
                await self._handle_error(e)
                
    @abstractmethod
    async def execute_cycle(self):
        """Execute one agent cycle - implement in subclasses"""
        pass
        
    async def _handle_error(self, error: Exception):
        """Handle errors - override for custom error handling"""
        self.state = AgentState.ERROR
        logger.error(f"Agent {self.name} error: {error}")
        
    async def send_message(self, message_type: str, payload: Dict,
                          recipient: Optional[str] = None,
                          priority: AgentPriority = AgentPriority.NORMAL):
        """Send message via bus"""
        message = AgentMessage(
            sender_id=self.id,
            recipient_id=recipient,
            message_type=message_type,
            payload=payload,
            priority=priority
        )
        await self.message_bus.publish(message)
        
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.agent_type,
            "state": self.state.value,
            "metrics": self.metrics.to_dict(),
            "uptime": time.time() - self._start_time if self._start_time else 0
        }


class AgentSwarm:
    """
    Coordinates multiple agents for complex financial operations
    """
    
    def __init__(self, name: str, message_bus: MessageBus):
        self.name = name
        self.id = str(uuid.uuid4())
        self.message_bus = message_bus
        self.agents: Dict[str, BaseAgent] = {}
        self.swarm_metrics = {
            "total_revenue": 0.0,
            "total_profit": 0.0,
            "active_agents": 0,
            "total_agents": 0
        }
        self._update_task: Optional[asyncio.Task] = None
        
    async def add_agent(self, agent: BaseAgent) -> str:
        """Add agent to swarm"""
        await agent.initialize()
        self.agents[agent.id] = agent
        self.swarm_metrics["total_agents"] = len(self.agents)
        
        # Subscribe to agent metrics updates
        self.message_bus.subscribe(f"metrics.{agent.id}", self._on_agent_metrics)
        
        logger.info(f"Agent {agent.name} added to swarm {self.name}")
        return agent.id
        
    async def remove_agent(self, agent_id: str):
        """Remove agent from swarm"""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            await agent.stop()
            del self.agents[agent_id]
            self.swarm_metrics["total_agents"] = len(self.agents)
            logger.info(f"Agent {agent.name} removed from swarm")
            
    async def start_all(self):
        """Start all agents in swarm"""
        await asyncio.gather(*[agent.start() for agent in self.agents.values()])
        self._update_task = asyncio.create_task(self._metrics_loop())
        logger.info(f"Swarm {self.name} started with {len(self.agents)} agents")
        
    async def stop_all(self):
        """Stop all agents in swarm"""
        if self._update_task:
            self._update_task.cancel()
        await asyncio.gather(*[agent.stop() for agent in self.agents.values()])
        logger.info(f"Swarm {self.name} stopped")
        
    async def _metrics_loop(self):
        """Update swarm metrics periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Update every minute
                self._recalculate_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics loop error: {e}")
                
    def _recalculate_metrics(self):
        """Recalculate aggregate metrics"""
        total_revenue = sum(a.metrics.total_revenue for a in self.agents.values())
        total_profit = sum(a.metrics.profit for a in self.agents.values())
        active = sum(1 for a in self.agents.values() if a.state == AgentState.RUNNING)
        
        self.swarm_metrics.update({
            "total_revenue": total_revenue,
            "total_profit": total_profit,
            "active_agents": active
        })
        
    async def _on_agent_metrics(self, message: AgentMessage):
        """Handle metrics updates from agents"""
        # Real-time metrics aggregation
        pass
        
    def get_swarm_status(self) -> Dict:
        """Get complete swarm status"""
        self._recalculate_metrics()
        return {
            "id": self.id,
            "name": self.name,
            "metrics": self.swarm_metrics,
            "agents": [a.get_status() for a in self.agents.values()]
        }
        
    def get_top_performers(self, limit: int = 5) -> List[Dict]:
        """Get top performing agents by profit"""
        sorted_agents = sorted(
            self.agents.values(),
            key=lambda a: a.metrics.profit,
            reverse=True
        )
        return [a.get_status() for a in sorted_agents[:limit]]


# Singleton message bus for the entire system
_global_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get global message bus instance"""
    global _global_message_bus
    if _global_message_bus is None:
        _global_message_bus = MessageBus()
    return _global_message_bus
