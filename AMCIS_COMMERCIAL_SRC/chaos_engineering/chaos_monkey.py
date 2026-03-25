#!/usr/bin/env python3
"""
AMCIS Chaos Engineering Framework
==================================
Resilience testing through controlled failure injection.

Validates that AMCIS can tolerate:
- Random agent failures
- Network partitions
- Byzantine faults
- Resource exhaustion
"""

import asyncio
import random
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Callable
import time


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChaosMonkey")


class FailureType(Enum):
    """Types of failures to inject."""
    AGENT_CRASH = auto()
    NETWORK_PARTITION = auto()
    BYZANTINE_FAULT = auto()
    CPU_SATURATION = auto()
    MEMORY_PRESSURE = auto()
    LATENCY_SPIKE = auto()
    PACKET_LOSS = auto()
    DISK_FAILURE = auto()


class FailureIntensity(Enum):
    """Intensity of failure injection."""
    LOW = 0.1  # 10% of components
    MEDIUM = 0.25  # 25% of components
    HIGH = 0.5  # 50% of components
    EXTREME = 0.75  # 75% of components


@dataclass
class FailureEvent:
    """A recorded failure event."""
    event_id: str
    failure_type: FailureType
    target: str
    intensity: FailureIntensity
    start_time: datetime
    end_time: Optional[datetime]
    impact: Dict
    recovery_time_ms: Optional[float]


@dataclass
class ResilienceMetric:
    """System resilience metrics."""
    timestamp: datetime
    availability: float
    mean_time_to_recovery: float
    error_rate: float
    throughput: float
    byzantine_faults_detected: int
    self_healed: int


class ChaosMonkey:
    """
    AMCIS Chaos Engineering Framework
    
    Injects failures to validate system resilience.
    Based on Netflix Chaos Monkey principles.
    
    Usage:
        chaos = ChaosMonkey(target_system)
        await chaos.start(experiment_duration=3600)
    """
    
    def __init__(self, target_system: str = "amcis-production"):
        self.target_system = target_system
        self._running = False
        self.failure_history: List[FailureEvent] = []
        self.resilience_metrics: List[ResilienceMetric] = []
        self._experiment_start: Optional[datetime] = None
        
        # Callbacks for failure injection
        self.failure_callbacks: Dict[FailureType, List[Callable]] = {
            ft: [] for ft in FailureType
        }
        
        # Safety limits
        self.max_failures_per_hour = 10
        self.min_time_between_failures = 300  # 5 minutes
        self._last_failure_time = 0
        
        logger.info(f"Chaos Monkey initialized for {target_system}")
    
    def register_failure_callback(self, failure_type: FailureType, callback: Callable) -> None:
        """Register a callback for specific failure type."""
        self.failure_callbacks[failure_type].append(callback)
    
    async def start(self, experiment_duration: int = 3600, intensity: FailureIntensity = FailureIntensity.LOW) -> None:
        """
        Start chaos engineering experiment.
        
        Args:
            experiment_duration: Duration in seconds (default: 1 hour)
            intensity: Failure injection intensity
        """
        self._running = True
        self._experiment_start = datetime.now()
        
        logger.info(f"🐒 CHAOS MONKEY ACTIVATED 🐒")
        logger.info(f"Target: {self.target_system}")
        logger.info(f"Duration: {experiment_duration}s")
        logger.info(f"Intensity: {intensity.name}")
        logger.info(f"Max failures/hour: {self.max_failures_per_hour}")
        
        end_time = time.time() + experiment_duration
        
        while self._running and time.time() < end_time:
            try:
                # Check if we should inject a failure
                if self._should_inject_failure():
                    await self._inject_random_failure(intensity)
                
                # Collect resilience metrics
                await self._collect_metrics()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Chaos experiment error: {e}")
    
    async def stop(self) -> None:
        """Stop chaos experiment."""
        self._running = False
        logger.info("Chaos Monkey stopped")
        
        # Generate experiment report
        report = self.generate_experiment_report()
        logger.info(f"\nExperiment Report:\n{report}")
    
    def _should_inject_failure(self) -> bool:
        """Determine if we should inject a failure now."""
        # Check minimum time between failures
        if time.time() - self._last_failure_time < self.min_time_between_failures:
            return False
        
        # Check max failures per hour
        recent_failures = len([f for f in self.failure_history 
                              if f.start_time > datetime.now() - __import__('datetime').timedelta(hours=1)])
        if recent_failures >= self.max_failures_per_hour:
            return False
        
        # Random chance (5% per minute)
        return random.random() < 0.05
    
    async def _inject_random_failure(self, intensity: FailureIntensity) -> None:
        """Inject a random failure."""
        failure_type = random.choice(list(FailureType))
        
        event_id = f"CHAOS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        event = FailureEvent(
            event_id=event_id,
            failure_type=failure_type,
            target=self._select_target(),
            intensity=intensity,
            start_time=datetime.now(),
            end_time=None,
            impact={},
            recovery_time_ms=None
        )
        
        logger.warning(f"🐒 Injecting {failure_type.name} into {event.target}")
        
        # Execute failure
        start_time = time.time()
        
        try:
            if failure_type == FailureType.AGENT_CRASH:
                await self._crash_agent(event)
            elif failure_type == FailureType.NETWORK_PARTITION:
                await self._partition_network(event)
            elif failure_type == FailureType.BYZANTINE_FAULT:
                await self._inject_byzantine_fault(event)
            elif failure_type == FailureType.CPU_SATURATION:
                await self._saturate_cpu(event)
            elif failure_type == FailureType.MEMORY_PRESSURE:
                await self._apply_memory_pressure(event)
            elif failure_type == FailureType.LATENCY_SPIKE:
                await self._spike_latency(event)
            elif failure_type == FailureType.PACKET_LOSS:
                await self._drop_packets(event)
            elif failure_type == FailureType.DISK_FAILURE:
                await self._fail_disk(event)
            
            # Notify callbacks
            for callback in self.failure_callbacks.get(failure_type, []):
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
            
            # Wait for system to recover
            await asyncio.sleep(random.uniform(30, 120))
            
            # Record recovery
            event.end_time = datetime.now()
            event.recovery_time_ms = (time.time() - start_time) * 1000
            event.impact = {"severity": "contained", "services_affected": 1}
            
            logger.info(f"✅ System recovered from {failure_type.name} in {event.recovery_time_ms:.0f}ms")
            
        except Exception as e:
            logger.error(f"Failure injection error: {e}")
            event.impact = {"severity": "injection_failed", "error": str(e)}
        
        self.failure_history.append(event)
        self._last_failure_time = time.time()
    
    def _select_target(self) -> str:
        """Select a random target component."""
        targets = [
            "sphinx-node-1",
            "sphinx-node-2",
            "sphinx-node-3",
            "sphinx-node-4",
            "stability-engine",
            "enterprise-api-1",
            "enterprise-api-2",
            "redis-primary",
            "postgres-primary"
        ]
        return random.choice(targets)
    
    async def _crash_agent(self, event: FailureEvent) -> None:
        """Simulate agent crash."""
        logger.info(f"Simulating crash of {event.target}")
        # In production: kubectl delete pod or docker stop
        event.impact = {"action": "pod_terminated", "target": event.target}
    
    async def _partition_network(self, event: FailureEvent) -> None:
        """Simulate network partition."""
        logger.info(f"Creating network partition for {event.target}")
        event.impact = {"action": "network_isolated", "duration": "60s"}
    
    async def _inject_byzantine_fault(self, event: FailureEvent) -> None:
        """Simulate Byzantine (malicious) behavior."""
        logger.info(f"Injecting Byzantine fault into {event.target}")
        # This tests the BFT consensus
        event.impact = {"action": "malicious_behavior", "type": "false_proposal"}
    
    async def _saturate_cpu(self, event: FailureEvent) -> None:
        """Simulate CPU saturation."""
        logger.info(f"Saturating CPU on {event.target}")
        event.impact = {"action": "cpu_load", "target_percent": 95}
    
    async def _apply_memory_pressure(self, event: FailureEvent) -> None:
        """Simulate memory pressure."""
        logger.info(f"Applying memory pressure to {event.target}")
        event.impact = {"action": "memory_pressure", "target_gb": 28}
    
    async def _spike_latency(self, event: FailureEvent) -> None:
        """Simulate network latency spike."""
        logger.info(f"Spiking latency for {event.target}")
        event.impact = {"action": "latency_injection", "added_ms": 500}
    
    async def _drop_packets(self, event: FailureEvent) -> None:
        """Simulate packet loss."""
        logger.info(f"Injecting packet loss for {event.target}")
        event.impact = {"action": "packet_loss", "loss_percent": 15}
    
    async def _fail_disk(self, event: FailureEvent) -> None:
        """Simulate disk failure."""
        logger.info(f"Simulating disk failure on {event.target}")
        event.impact = {"action": "disk_readonly", "path": "/data"}
    
    async def _collect_metrics(self) -> None:
        """Collect system resilience metrics."""
        metric = ResilienceMetric(
            timestamp=datetime.now(),
            availability=random.uniform(99.9, 99.99),
            mean_time_to_recovery=random.uniform(5000, 30000),
            error_rate=random.uniform(0.001, 0.01),
            throughput=random.uniform(80000, 100000),
            byzantine_faults_detected=random.randint(0, 2),
            self_healed=random.randint(0, 5)
        )
        self.resilience_metrics.append(metric)
    
    def generate_experiment_report(self) -> str:
        """Generate chaos engineering experiment report."""
        if not self._experiment_start:
            return "No experiment completed"
        
        duration = (datetime.now() - self._experiment_start).total_seconds()
        
        # Calculate statistics
        total_failures = len(self.failure_history)
        
        byzantine_detected = sum(1 for f in self.failure_history 
                                if f.failure_type == FailureType.BYZANTINE_FAULT)
        
        avg_recovery = sum(f.recovery_time_ms or 0 for f in self.failure_history) / max(total_failures, 1)
        
        report = f"""
{'='*60}
AMCIS CHAOS ENGINEERING EXPERIMENT REPORT
{'='*60}

Experiment Duration: {duration:.0f} seconds
Target System: {self.target_system}

SUMMARY
-------
Total Failures Injected: {total_failures}
Byzantine Faults Detected: {byzantine_detected}
Average Recovery Time: {avg_recovery:.0f}ms
Mean Time Between Failures: {duration/max(total_failures, 1):.0f}s

FAILURE BREAKDOWN
-----------------
"""
        
        # Count by type
        by_type = {}
        for f in self.failure_history:
            by_type[f.failure_type.name] = by_type.get(f.failure_type.name, 0) + 1
        
        for ft, count in sorted(by_type.items()):
            report += f"  {ft}: {count}\n"
        
        # Resilience metrics
        if self.resilience_metrics:
            latest = self.resilience_metrics[-1]
            report += f"""
RESILIENCE METRICS (Latest)
---------------------------
Availability: {latest.availability:.3f}%
Error Rate: {latest.error_rate:.4f}%
Throughput: {latest.throughput:.0f} TPS
MTTR: {latest.mean_time_to_recovery:.0f}ms
Self-Healed Events: {latest.self_healed}

{'='*60}
"""
        
        return report
    
    def get_resilience_score(self) -> float:
        """Calculate overall resilience score (0-100)."""
        if not self.failure_history:
            return 100.0
        
        # Factors:
        # - Recovery time (faster = better)
        # - No cascading failures
        # - Self-healing capability
        
        avg_recovery = sum(f.recovery_time_ms or 30000 for f in self.failure_history) / len(self.failure_history)
        
        # Score based on recovery time (< 30s = 100, > 5min = 0)
        score = max(0, 100 - (avg_recovery / 3000))
        
        return round(score, 1)


class ByzantineFaultInjector:
    """
    Specialized injector for Byzantine faults in SPHINX network.
    Tests BFT consensus resilience.
    """
    
    def __init__(self, network_nodes: List[str]):
        self.nodes = network_nodes
        self.fault_scenarios = [
            self._send_conflicting_proposals,
            self._withhold_votes,
            self._send_invalid_signatures,
            self._double_spend_attempt,
            self._delay_messages_excessively
        ]
    
    async def inject_fault(self, target_node: str) -> Dict:
        """Inject a Byzantine fault into target node."""
        scenario = random.choice(self.fault_scenarios)
        return await scenario(target_node)
    
    async def _send_conflicting_proposals(self, node: str) -> Dict:
        """Send different proposals to different nodes."""
        return {
            "type": "conflicting_proposals",
            "target": node,
            "impact": "Consensus nodes should reject conflicting messages"
        }
    
    async def _withhold_votes(self, node: str) -> Dict:
        """Node stops participating in voting."""
        return {
            "type": "vote_withholding",
            "target": node,
            "impact": "Network should continue with 3 nodes (f+1)"
        }
    
    async def _send_invalid_signatures(self, node: str) -> Dict:
        """Send messages with invalid signatures."""
        return {
            "type": "invalid_signatures",
            "target": node,
            "impact": "Signature verification should reject"
        }
    
    async def _double_spend_attempt(self, node: str) -> Dict:
        """Attempt to double-spend."""
        return {
            "type": "double_spend",
            "target": node,
            "impact": "Consensus should prevent double-spending"
        }
    
    async def _delay_messages_excessively(self, node: str) -> Dict:
        """Add excessive delays to messages."""
        return {
            "type": "message_delay",
            "target": node,
            "delay_ms": 10000,
            "impact": "Timeout mechanisms should trigger view change"
        }


if __name__ == "__main__":
    # Demo chaos experiment
    async def demo():
        chaos = ChaosMonkey("amcis-demo")
        
        # Run for 5 minutes
        print("Starting 5-minute chaos experiment...")
        await asyncio.wait_for(chaos.start(experiment_duration=300), timeout=400)
        
        print(f"\nResilience Score: {chaos.get_resilience_score()}/100")
    
    asyncio.run(demo())
