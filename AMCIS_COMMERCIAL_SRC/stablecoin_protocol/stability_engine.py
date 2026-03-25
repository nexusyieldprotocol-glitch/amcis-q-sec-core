#!/usr/bin/env python3
"""
AMCIS™ Stability Engine
=======================
AI-powered algorithmic stability maintenance system.

Maintains five-factor equilibrium:
1. FCR (Foreign Currency Reserves) - Target: 0.55
2. LFI (Liquidity Flow Index) - Target: 0.15  
3. GCS (Global Confidence Score) - Target: 0.40
4. VSI (Velocity Stability Index) - Target: 0.50
5. SER (Systemic Elasticity Reserve) - Target: 0.70

Commercial Version - Requires License
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
from collections import deque

from .pid_controller import PIDController


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StabilityEngine")


class StabilityMode(Enum):
    """Operational modes for stability engine."""
    PASSIVE = "passive"  # Monitor only
    ACTIVE = "active"    # PID control enabled
    AGGRESSIVE = "aggressive"  # High responsiveness
    EMERGENCY = "emergency"  # Emergency interventions
    MAINTENANCE = "maintenance"  # Manual override


@dataclass
class StabilityMetrics:
    """Five-factor stability metrics."""
    fcr: float  # Foreign Currency Reserves (0-1)
    lfi: float  # Liquidity Flow Index (0-1)
    gcs: float  # Global Confidence Score (0-1)
    vsi: float  # Velocity Stability Index (0-1)
    ser: float  # Systemic Elasticity Reserve (0-1)
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Composite scores
    @property
    def overall_stability(self) -> float:
        """Calculate overall stability score (weighted average)."""
        weights = {
            'fcr': 0.25,
            'lfi': 0.20,
            'gcs': 0.20,
            'vsi': 0.15,
            'ser': 0.20
        }
        return (
            self.fcr * weights['fcr'] +
            self.lfi * weights['lfi'] +
            self.gcs * weights['gcs'] +
            self.vsi * weights['vsi'] +
            self.ser * weights['ser']
        )
    
    @property
    def deviation_score(self) -> float:
        """Calculate deviation from optimal targets."""
        targets = {
            'fcr': 0.55,
            'lfi': 0.15,
            'gcs': 0.40,
            'vsi': 0.50,
            'ser': 0.70
        }
        
        deviations = [
            abs(self.fcr - targets['fcr']),
            abs(self.lfi - targets['lfi']),
            abs(self.gcs - targets['gcs']),
            abs(self.vsi - targets['vsi']),
            abs(self.ser - targets['ser'])
        ]
        
        return sum(deviations) / len(deviations)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'fcr': self.fcr,
            'lfi': self.lfi,
            'gcs': self.gcs,
            'vsi': self.vsi,
            'ser': self.ser,
            'overall_stability': self.overall_stability,
            'deviation_score': self.deviation_score,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Adjustment:
    """A stability adjustment decision."""
    adjustment_id: str
    metric: str
    current_value: float
    target_value: float
    adjustment_amount: float
    confidence: float
    reasoning: str
    timestamp: datetime
    executed: bool = False


class StabilityEngine:
    """
    AMCIS Stability Engine
    
    Maintains algorithmic stability through:
    - Real-time metric monitoring
    - PID control for smooth adjustments
    - Multi-factor equilibrium maintenance
    - Predictive stability modeling
    
    Args:
        mode: Operating mode (default: ACTIVE)
        update_interval: Seconds between updates (default: 60)
    """
    
    # Optimal targets for each metric
    TARGETS = {
        'fcr': 0.55,
        'lfi': 0.15,
        'gcs': 0.40,
        'vsi': 0.50,
        'ser': 0.70
    }
    
    def __init__(
        self,
        mode: StabilityMode = StabilityMode.ACTIVE,
        update_interval: float = 60.0
    ):
        self.mode = mode
        self.update_interval = update_interval
        
        # PID controllers for each metric
        self.pids = {
            'fcr': PIDController(kp=0.5, ki=0.1, kd=0.05),
            'lfi': PIDController(kp=0.3, ki=0.05, kd=0.02),
            'gcs': PIDController(kp=0.4, ki=0.08, kd=0.04),
            'vsi': PIDController(kp=0.35, ki=0.06, kd=0.03),
            'ser': PIDController(kp=0.45, ki=0.09, kd=0.045)
        }
        
        # Current metrics
        self.current_metrics: Optional[StabilityMetrics] = None
        self.metrics_history: deque = deque(maxlen=1000)
        
        # Adjustments
        self.pending_adjustments: List[Adjustment] = []
        self.executed_adjustments: List[Adjustment] = []
        
        # Callbacks
        self.metric_callbacks: List[Callable] = []
        self.adjustment_callbacks: List[Callable] = []
        
        # Control
        self._running = False
        self._adjustment_count = 0
        
        logger.info(f"Stability Engine initialized in {mode.value} mode")
    
    async def start(self) -> None:
        """Start the stability engine."""
        logger.info("Starting Stability Engine...")
        self._running = True
        
        # Initialize with neutral metrics
        self.current_metrics = StabilityMetrics(
            fcr=0.55,
            lfi=0.15,
            gcs=0.40,
            vsi=0.50,
            ser=0.70
        )
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
        
        logger.info("Stability Engine started")
    
    async def stop(self) -> None:
        """Stop the stability engine."""
        logger.info("Stopping Stability Engine...")
        self._running = False
        logger.info("Stability Engine stopped")
    
    def update_metrics(self, metrics: StabilityMetrics) -> None:
        """
        Update current stability metrics.
        
        Args:
            metrics: New stability metrics
        """
        self.current_metrics = metrics
        self.metrics_history.append(metrics)
        
        # Notify callbacks
        for callback in self.metric_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Metric callback error: {e}")
        
        # Calculate and queue adjustments if in active mode
        if self.mode in [StabilityMode.ACTIVE, StabilityMode.AGGRESSIVE]:
            self._calculate_adjustments(metrics)
    
    def get_adjustments(self) -> List[Adjustment]:
        """Get list of pending adjustments."""
        return self.pending_adjustments.copy()
    
    def execute_adjustment(self, adjustment_id: str) -> bool:
        """
        Execute a pending adjustment.
        
        Args:
            adjustment_id: ID of adjustment to execute
            
        Returns:
            True if executed successfully
        """
        for adj in self.pending_adjustments:
            if adj.adjustment_id == adjustment_id:
                adj.executed = True
                self.executed_adjustments.append(adj)
                self.pending_adjustments.remove(adj)
                
                logger.info(f"Executed adjustment: {adj.metric} by {adj.adjustment_amount:.4f}")
                
                # Notify callbacks
                for callback in self.adjustment_callbacks:
                    try:
                        callback(adj)
                    except Exception as e:
                        logger.error(f"Adjustment callback error: {e}")
                
                return True
        
        return False
    
    def get_stability_report(self) -> Dict:
        """Generate comprehensive stability report."""
        if not self.current_metrics:
            return {"error": "No metrics available"}
        
        # Calculate trends
        trends = self._calculate_trends()
        
        # Risk assessment
        risk_level = self._assess_risk()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "current_metrics": self.current_metrics.to_dict(),
            "trends": trends,
            "risk_assessment": risk_level,
            "mode": self.mode.value,
            "pending_adjustments": len(self.pending_adjustments),
            "executed_adjustments": len(self.executed_adjustments),
            "recommendations": self._generate_recommendations()
        }
    
    def on_metric_update(self, callback: Callable[[StabilityMetrics], None]) -> None:
        """Register callback for metric updates."""
        self.metric_callbacks.append(callback)
    
    def on_adjustment(self, callback: Callable[[Adjustment], None]) -> None:
        """Register callback for adjustments."""
        self.adjustment_callbacks.append(callback)
    
    def set_mode(self, mode: StabilityMode) -> None:
        """Change operating mode."""
        logger.info(f"Changing mode from {self.mode.value} to {mode.value}")
        self.mode = mode
        
        # Adjust PID parameters based on mode
        if mode == StabilityMode.AGGRESSIVE:
            for pid in self.pids.values():
                pid.kp *= 2.0
        elif mode == StabilityMode.PASSIVE:
            for pid in self.pids.values():
                pid.kp *= 0.5
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                if self.current_metrics:
                    # Auto-execute high-confidence adjustments
                    if self.mode == StabilityMode.AGGRESSIVE:
                        for adj in self.pending_adjustments[:]:
                            if adj.confidence > 0.8:
                                self.execute_adjustment(adj.adjustment_id)
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(1)
    
    def _calculate_adjustments(self, metrics: StabilityMetrics) -> None:
        """Calculate needed adjustments based on metrics."""
        current_values = {
            'fcr': metrics.fcr,
            'lfi': metrics.lfi,
            'gcs': metrics.gcs,
            'vsi': metrics.vsi,
            'ser': metrics.ser
        }
        
        for metric, current in current_values.items():
            target = self.TARGETS[metric]
            error = target - current
            
            # Skip if within tolerance
            if abs(error) < 0.01:
                continue
            
            # Calculate PID adjustment
            pid = self.pids[metric]
            adjustment = pid.update(error)
            
            # Limit adjustment magnitude
            adjustment = max(-0.1, min(0.1, adjustment))
            
            # Calculate confidence
            confidence = 1.0 - abs(error)
            confidence = max(0.5, min(1.0, confidence))
            
            # Create adjustment
            self._adjustment_count += 1
            adj = Adjustment(
                adjustment_id=f"adj-{self._adjustment_count}",
                metric=metric,
                current_value=current,
                target_value=target,
                adjustment_amount=adjustment,
                confidence=confidence,
                reasoning=f"PID correction for {metric}: error={error:.4f}",
                timestamp=datetime.now()
            )
            
            self.pending_adjustments.append(adj)
            logger.debug(f"Calculated adjustment: {adj.metric} -> {adj.adjustment_amount:.4f}")
    
    def _calculate_trends(self) -> Dict:
        """Calculate metric trends from history."""
        if len(self.metrics_history) < 2:
            return {"status": "insufficient_data"}
        
        # Get last 10 measurements
        recent = list(self.metrics_history)[-10:]
        
        trends = {}
        for metric in ['fcr', 'lfi', 'gcs', 'vsi', 'ser']:
            values = [getattr(m, metric) for m in recent]
            
            if len(values) >= 2:
                # Simple linear trend
                trend = (values[-1] - values[0]) / len(values)
                direction = "increasing" if trend > 0.001 else "decreasing" if trend < -0.001 else "stable"
                
                trends[metric] = {
                    "direction": direction,
                    "rate": abs(trend),
                    "current": values[-1]
                }
        
        return trends
    
    def _assess_risk(self) -> Dict:
        """Assess current risk level."""
        if not self.current_metrics:
            return {"level": "unknown"}
        
        deviation = self.current_metrics.deviation_score
        
        if deviation < 0.05:
            level = "low"
            color = "green"
        elif deviation < 0.15:
            level = "moderate"
            color = "yellow"
        elif deviation < 0.30:
            level = "high"
            color = "orange"
        else:
            level = "critical"
            color = "red"
        
        return {
            "level": level,
            "color": color,
            "deviation_score": deviation,
            "overall_stability": self.current_metrics.overall_stability
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate stability recommendations."""
        recommendations = []
        
        if not self.current_metrics:
            return recommendations
        
        metrics = self.current_metrics
        
        if metrics.fcr < 0.50:
            recommendations.append("Increase foreign currency reserves")
        
        if metrics.lfi > 0.20:
            recommendations.append("Reduce liquidity flow volatility")
        
        if metrics.gcs < 0.35:
            recommendations.append("Implement confidence-building measures")
        
        if metrics.vsi < 0.45:
            recommendations.append("Stabilize transaction velocity")
        
        if metrics.ser < 0.65:
            recommendations.append("Build systemic elasticity reserves")
        
        return recommendations
