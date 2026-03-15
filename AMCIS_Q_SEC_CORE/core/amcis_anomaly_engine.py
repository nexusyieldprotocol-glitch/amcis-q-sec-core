"""
AMCIS Anomaly Detection Engine
==============================

Implements behavioral anomaly detection using:
- Isolation Forest for outlier detection
- One-Class SVM for novelty detection
- Statistical profiling

NIST Alignment: SP 800-53 (SI-4 Information System Monitoring)
"""

import asyncio
import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Deque, Callable

import numpy as np
import structlog


class AnomalyType(Enum):
    """Types of detected anomalies."""
    FILE_ACCESS_ANOMALY = auto()
    COMMAND_FREQUENCY_ANOMALY = auto()
    PROCESS_SPAWN_ANOMALY = auto()
    NETWORK_ANOMALY = auto()
    MEMORY_ANOMALY = auto()
    SYSCALL_ANOMALY = auto()


class DetectionMethod(Enum):
    """Anomaly detection methods."""
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    STATISTICAL = "statistical"
    HEURISTIC = "heuristic"


@dataclass
class FeatureVector:
    """Feature vector for anomaly detection."""
    command_count: float
    file_access_rate: float
    network_connections: float
    process_spawn_rate: float
    syscall_diversity: float
    entropy_score: float
    timestamp: float = field(default_factory=time.time)
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([
            self.command_count,
            self.file_access_rate,
            self.network_connections,
            self.process_spawn_rate,
            self.syscall_diversity,
            self.entropy_score
        ])
    
    @classmethod
    def feature_names(cls) -> List[str]:
        """Get feature names."""
        return [
            "command_count",
            "file_access_rate",
            "network_connections",
            "process_spawn_rate",
            "syscall_diversity",
            "entropy_score"
        ]


@dataclass
class AnomalyReport:
    """Anomaly detection report."""
    anomaly_type: AnomalyType
    confidence: float  # 0.0 to 1.0
    severity: int  # 1-10
    detection_method: DetectionMethod
    feature_vector: FeatureVector
    details: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    correlation_id: str = field(default_factory=lambda: hashlib.sha256(
        str(time.time_ns()).encode()
    ).hexdigest()[:16])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "anomaly_type": self.anomaly_type.name,
            "confidence": self.confidence,
            "severity": self.severity,
            "detection_method": self.detection_method.value,
            "features": {
                k: getattr(self.feature_vector, k)
                for k in FeatureVector.feature_names()
            },
            "details": self.details,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id
        }


class IsolationForestDetector:
    """
    Isolation Forest anomaly detector implementation.
    
    Isolation Forest isolates anomalies by randomly selecting a feature
    and randomly selecting a split value between max and min of that feature.
    """
    
    def __init__(
        self,
        n_trees: int = 100,
        sample_size: int = 256,
        contamination: float = 0.1
    ) -> None:
        """
        Initialize Isolation Forest.
        
        Args:
            n_trees: Number of trees in forest
            sample_size: Subsample size for each tree
            contamination: Expected anomaly proportion
        """
        self.n_trees = n_trees
        self.sample_size = min(sample_size, 256)
        self.contamination = contamination
        self.trees: List[Dict] = []
        self.threshold: float = 0.5
        self._fitted = False
    
    def fit(self, X: np.ndarray) -> None:
        """
        Fit the Isolation Forest to normal data.
        
        Args:
            X: Training data (n_samples, n_features)
        """
        n_samples = min(len(X), self.sample_size)
        
        self.trees = []
        for _ in range(self.n_trees):
            # Sample data
            indices = np.random.choice(len(X), n_samples, replace=False)
            sample = X[indices]
            
            # Build tree
            tree = self._build_tree(sample, 0, 10)
            self.trees.append(tree)
        
        # Calculate threshold
        scores = self.decision_function(X)
        self.threshold = np.percentile(scores, self.contamination * 100)
        self._fitted = True
    
    def _build_tree(
        self,
        X: np.ndarray,
        current_height: int,
        height_limit: int
    ) -> Dict:
        """Build isolation tree."""
        if current_height >= height_limit or len(X) <= 1:
            return {
                "type": "external",
                "size": len(X),
                "height": current_height
            }
        
        # Select random feature
        feature_idx = np.random.randint(0, X.shape[1])
        feature_values = X[:, feature_idx]
        
        if len(np.unique(feature_values)) <= 1:
            return {
                "type": "external",
                "size": len(X),
                "height": current_height
            }
        
        # Select random split point
        split_value = np.random.uniform(
            feature_values.min(),
            feature_values.max()
        )
        
        # Split data
        left_mask = feature_values < split_value
        right_mask = ~left_mask
        
        return {
            "type": "internal",
            "feature": feature_idx,
            "split": split_value,
            "left": self._build_tree(X[left_mask], current_height + 1, height_limit),
            "right": self._build_tree(X[right_mask], current_height + 1, height_limit)
        }
    
    def _path_length(self, x: np.ndarray, tree: Dict) -> float:
        """Calculate path length for sample."""
        if tree["type"] == "external":
            return tree["height"] + self._c_factor(tree["size"])
        
        if x[tree["feature"]] < tree["split"]:
            return self._path_length(x, tree["left"])
        else:
            return self._path_length(x, tree["right"])
    
    def _c_factor(self, size: int) -> float:
        """Calculate average path length for unsuccessful search."""
        if size <= 1:
            return 0.0
        return 2.0 * (np.log(size - 1) + 0.5772156649) - 2.0 * (size - 1) / size
    
    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """
        Calculate anomaly scores.
        
        Args:
            X: Samples to score
            
        Returns:
            Anomaly scores (higher = more anomalous)
        """
        scores = np.zeros(len(X))
        
        for i, x in enumerate(X):
            path_lengths = [
                self._path_length(x, tree) for tree in self.trees
            ]
            avg_path = np.mean(path_lengths)
            # Convert to anomaly score
            scores[i] = 2.0 ** (-avg_path / self._c_factor(self.sample_size))
        
        return scores
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomalies.
        
        Args:
            X: Samples to predict
            
        Returns:
            1 for normal, -1 for anomaly
        """
        scores = self.decision_function(X)
        return np.where(scores > self.threshold, -1, 1)


class OneClassSVMDetector:
    """
    One-Class SVM anomaly detector.
    
    Learns a decision boundary for normal data and identifies
    samples falling outside as anomalies.
    """
    
    def __init__(
        self,
        nu: float = 0.1,
        gamma: float = 0.1
    ) -> None:
        """
        Initialize One-Class SVM.
        
        Args:
            nu: Upper bound on training errors / lower bound on support vectors
            gamma: Kernel coefficient
        """
        self.nu = nu
        self.gamma = gamma
        self.support_vectors: Optional[np.ndarray] = None
        self.alpha: Optional[np.ndarray] = None
        self.rho: float = 0.0
        self._fitted = False
    
    def fit(self, X: np.ndarray) -> None:
        """
        Fit One-Class SVM.
        
        Args:
            X: Training data
        """
        # Simplified implementation using gradient descent
        n_samples, n_features = X.shape
        
        # Initialize support vectors (subset of data)
        n_sv = max(1, int(self.nu * n_samples))
        indices = np.random.choice(n_samples, n_sv, replace=False)
        self.support_vectors = X[indices]
        
        # RBF kernel matrix
        K = self._rbf_kernel(self.support_vectors, self.support_vectors)
        
        # Initialize alphas
        self.alpha = np.ones(n_sv) / n_sv
        
        # Simple gradient descent for dual optimization
        learning_rate = 0.01
        for _ in range(1000):
            gradient = K @ self.alpha - 1.0
            self.alpha -= learning_rate * gradient
            
            # Project to feasible region
            self.alpha = np.maximum(self.alpha, 0)
            self.alpha /= np.sum(self.alpha) + 1e-10
        
        # Calculate rho (offset)
        self.rho = np.median(self._decision_function(X))
        self._fitted = True
    
    def _rbf_kernel(self, X: np.ndarray, Y: np.ndarray) -> np.ndarray:
        """RBF kernel computation."""
        sq_dists = (
            np.sum(X**2, axis=1).reshape(-1, 1) +
            np.sum(Y**2, axis=1) -
            2 * np.dot(X, Y.T)
        )
        return np.exp(-self.gamma * sq_dists)
    
    def _decision_function(self, X: np.ndarray) -> np.ndarray:
        """Calculate decision function values."""
        K = self._rbf_kernel(X, self.support_vectors)
        return K @ self.alpha - self.rho
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict anomalies.
        
        Returns:
            1 for normal, -1 for anomaly
        """
        scores = self._decision_function(X)
        return np.where(scores < 0, -1, 1)
    
    def decision_function(self, X: np.ndarray) -> np.ndarray:
        """Calculate anomaly scores."""
        return -self._decision_function(X)


class AnomalyEngine:
    """
    AMCIS Anomaly Detection Engine
    ==============================
    
    Multi-algorithm behavioral anomaly detection with real-time
    profiling and adaptive thresholds.
    """
    
    # Configuration
    BASELINE_WINDOW_SIZE = 1000
    ANOMALY_THRESHOLD = 0.7
    CRITICAL_ANOMALY_THRESHOLD = 0.85
    
    def __init__(
        self,
        kernel=None,
        enable_isolation_forest: bool = True,
        enable_one_class_svm: bool = True
    ) -> None:
        """
        Initialize anomaly engine.
        
        Args:
            kernel: AMCIS kernel reference
            enable_isolation_forest: Enable Isolation Forest detector
            enable_one_class_svm: Enable One-Class SVM detector
        """
        self.kernel = kernel
        self.logger = structlog.get_logger("amcis.anomaly_engine")
        
        # Detectors
        self.if_detector: Optional[IsolationForestDetector] = None
        self.svm_detector: Optional[OneClassSVMDetector] = None
        
        if enable_isolation_forest:
            self.if_detector = IsolationForestDetector(
                n_trees=100,
                sample_size=256,
                contamination=0.1
            )
        
        if enable_one_class_svm:
            self.svm_detector = OneClassSVMDetector(nu=0.1, gamma=0.1)
        
        # Baseline data
        self._baseline_data: Deque[FeatureVector] = deque(
            maxlen=self.BASELINE_WINDOW_SIZE
        )
        self._is_baseline_established = False
        
        # Activity tracking
        self._command_history: Deque[Tuple[float, str]] = deque(maxlen=1000)
        self._file_access_history: Deque[Tuple[float, str]] = deque(maxlen=1000)
        self._process_spawn_history: Deque[float] = deque(maxlen=1000)
        
        # Callbacks
        self._anomaly_callbacks: List[Callable[[AnomalyReport], None]] = []
        
        self.logger.info("anomaly_engine_initialized")
    
    def register_anomaly_callback(
        self,
        callback: Callable[[AnomalyReport], None]
    ) -> None:
        """Register callback for anomaly detection."""
        self._anomaly_callbacks.append(callback)
    
    def record_command(self, command: str) -> None:
        """Record command execution."""
        self._command_history.append((time.time(), command))
    
    def record_file_access(self, path: str) -> None:
        """Record file access."""
        self._file_access_history.append((time.time(), path))
    
    def record_process_spawn(self) -> None:
        """Record process spawn."""
        self._process_spawn_history.append(time.time())
    
    def _calculate_current_features(self) -> FeatureVector:
        """Calculate current feature vector."""
        now = time.time()
        window = 60.0  # 1 minute window
        
        # Count events in window
        command_count = sum(
            1 for t, _ in self._command_history
            if now - t < window
        )
        
        file_access_rate = sum(
            1 for t, _ in self._file_access_history
            if now - t < window
        ) / 60.0
        
        process_spawn_rate = sum(
            1 for t in self._process_spawn_history
            if now - t < window
        ) / 60.0
        
        # Calculate command entropy
        recent_commands = [
            cmd for t, cmd in self._command_history
            if now - t < window
        ]
        entropy = self._calculate_entropy(recent_commands)
        
        return FeatureVector(
            command_count=float(command_count),
            file_access_rate=file_access_rate,
            network_connections=0.0,  # Placeholder
            process_spawn_rate=process_spawn_rate,
            syscall_diversity=0.5,  # Placeholder
            entropy_score=entropy
        )
    
    def _calculate_entropy(self, items: List[str]) -> float:
        """Calculate Shannon entropy of items."""
        if not items:
            return 0.0
        
        from collections import Counter
        counts = Counter(items)
        total = len(items)
        
        import math
        entropy = 0.0
        for count in counts.values():
            p = count / total
            entropy -= p * math.log2(p)
        
        # Normalize to 0-1 range (assuming max entropy ~5)
        return min(1.0, entropy / 5.0)
    
    async def analyze(self) -> Optional[AnomalyReport]:
        """
        Perform anomaly analysis.
        
        Returns:
            Anomaly report if anomaly detected, None otherwise
        """
        features = self._calculate_current_features()
        
        # Add to baseline
        if not self._is_baseline_established:
            self._baseline_data.append(features)
            
            if len(self._baseline_data) >= 100:
                await self._establish_baseline()
            
            return None
        
        # Run detection algorithms
        anomaly_score = 0.0
        detection_methods = []
        
        # Isolation Forest
        if self.if_detector and self.if_detector._fitted:
            if_score = self.if_detector.decision_function(
                features.to_array().reshape(1, -1)
            )[0]
            anomaly_score = max(anomaly_score, if_score)
            detection_methods.append(DetectionMethod.ISOLATION_FOREST)
        
        # One-Class SVM
        if self.svm_detector and self.svm_detector._fitted:
            svm_score = self.svm_detector.decision_function(
                features.to_array().reshape(1, -1)
            )[0]
            # Normalize SVM score to 0-1
            svm_score = 1.0 / (1.0 + np.exp(-svm_score))
            anomaly_score = max(anomaly_score, svm_score)
            detection_methods.append(DetectionMethod.ONE_CLASS_SVM)
        
        # Statistical check
        stat_score = self._statistical_check(features)
        anomaly_score = max(anomaly_score, stat_score)
        detection_methods.append(DetectionMethod.STATISTICAL)
        
        # Determine if anomaly
        if anomaly_score >= self.ANOMALY_THRESHOLD:
            # Classify anomaly type
            anomaly_type = self._classify_anomaly(features)
            
            # Calculate severity
            severity = min(10, int(anomaly_score * 10))
            if anomaly_score >= self.CRITICAL_ANOMALY_THRESHOLD:
                severity = min(10, severity + 2)
            
            report = AnomalyReport(
                anomaly_type=anomaly_type,
                confidence=anomaly_score,
                severity=severity,
                detection_method=detection_methods[0],
                feature_vector=features,
                details={
                    "detection_methods": [m.value for m in detection_methods],
                    "baseline_size": len(self._baseline_data)
                }
            )
            
            self.logger.warning(
                "anomaly_detected",
                anomaly_type=anomaly_type.name,
                confidence=anomaly_score,
                severity=severity
            )
            
            # Notify callbacks
            for callback in self._anomaly_callbacks:
                try:
                    callback(report)
                except Exception as e:
                    self.logger.error("callback_error", error=str(e))
            
            # Notify kernel
            if self.kernel:
                await self.kernel.emit_event(
                    event_type=self.kernel.__class__.__dict__.get(
                        'SecurityEvent', {}
                    ).get('ANOMALY_DETECTED'),
                    source_module="anomaly_engine",
                    severity=severity,
                    data=report.to_dict()
                )
            
            return report
        
        return None
    
    async def _establish_baseline(self) -> None:
        """Establish baseline from collected data."""
        if len(self._baseline_data) < 50:
            return
        
        X = np.array([f.to_array() for f in self._baseline_data])
        
        # Fit detectors
        if self.if_detector:
            try:
                self.if_detector.fit(X)
                self.logger.info("isolation_forest_baseline_established")
            except Exception as e:
                self.logger.error("if_fit_error", error=str(e))
        
        if self.svm_detector:
            try:
                self.svm_detector.fit(X)
                self.logger.info("one_class_svm_baseline_established")
            except Exception as e:
                self.logger.error("svm_fit_error", error=str(e))
        
        self._is_baseline_established = True
        self.logger.info(
            "baseline_established",
            sample_size=len(self._baseline_data)
        )
    
    def _statistical_check(self, features: FeatureVector) -> float:
        """
        Statistical anomaly check using z-scores.
        
        Args:
            features: Current feature vector
            
        Returns:
            Anomaly score
        """
        if len(self._baseline_data) < 30:
            return 0.0
        
        X = np.array([f.to_array() for f in self._baseline_data])
        current = features.to_array()
        
        # Calculate z-scores
        means = np.mean(X, axis=0)
        stds = np.std(X, axis=0) + 1e-10
        z_scores = np.abs((current - means) / stds)
        
        # Max z-score as anomaly indicator
        max_z = np.max(z_scores)
        
        # Convert to 0-1 score (sigmoid)
        return 1.0 / (1.0 + np.exp(-(max_z - 2) / 2))
    
    def _classify_anomaly(self, features: FeatureVector) -> AnomalyType:
        """Classify anomaly type based on features."""
        # Simple rule-based classification
        feature_values = {
            "command_count": features.command_count,
            "file_access_rate": features.file_access_rate,
            "process_spawn_rate": features.process_spawn_rate,
            "entropy": features.entropy_score
        }
        
        # Find most anomalous feature
        max_feature = max(feature_values, key=feature_values.get)
        
        classification_map = {
            "command_count": AnomalyType.COMMAND_FREQUENCY_ANOMALY,
            "file_access_rate": AnomalyType.FILE_ACCESS_ANOMALY,
            "process_spawn_rate": AnomalyType.PROCESS_SPAWN_ANOMALY,
            "entropy": AnomalyType.SYSCALL_ANOMALY
        }
        
        return classification_map.get(max_feature, AnomalyType.SYSCALL_ANOMALY)
    
    def get_status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "baseline_established": self._is_baseline_established,
            "baseline_samples": len(self._baseline_data),
            "command_history_size": len(self._command_history),
            "isolation_forest_ready": (
                self.if_detector._fitted if self.if_detector else False
            ),
            "one_class_svm_ready": (
                self.svm_detector._fitted if self.svm_detector else False
            )
        }
