"""
Tests for AMCIS Kernel module.
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.amcis_kernel import AMCISKernel, KernelState, SecurityEvent


class TestAMCISKernel:
    """Test cases for AMCISKernel."""
    
    @pytest.fixture
    def kernel(self):
        """Create a fresh kernel instance for each test."""
        AMCISKernel._instance = None
        return AMCISKernel(enable_tpm=False)
    
    def test_singleton_pattern(self, kernel):
        """Test that kernel is a singleton."""
        kernel2 = AMCISKernel()
        assert kernel is kernel2
    
    def test_initial_state(self, kernel):
        """Test initial kernel state."""
        assert kernel.get_state() == KernelState.INITIALIZING
    
    @pytest.mark.asyncio
    async def test_secure_boot(self, kernel):
        """Test secure boot sequence."""
        with patch.object(kernel, '_verify_self_integrity', return_value=True):
            with patch.object(kernel, '_tpm_attestation', return_value=True):
                with patch.object(kernel, '_detect_debugger', return_value=False):
                    result = await kernel.secure_boot()
                    assert result is True
                    assert kernel.get_state() == KernelState.OPERATIONAL
    
    @pytest.mark.asyncio
    async def test_secure_boot_integrity_failure(self, kernel):
        """Test secure boot with integrity failure."""
        with patch.object(kernel, '_verify_self_integrity', return_value=False):
            result = await kernel.secure_boot()
            assert result is False
            assert kernel.get_state() == KernelState.LOCKDOWN
    
    def test_module_registration(self, kernel):
        """Test module registration."""
        mock_module = MagicMock()
        kernel.register_module("test_module", mock_module)
        
        assert kernel.get_module("test_module") is mock_module
    
    def test_duplicate_module_registration(self, kernel):
        """Test that duplicate module registration raises error."""
        mock_module = MagicMock()
        kernel.register_module("test_module", mock_module)
        
        with pytest.raises(ValueError):
            kernel.register_module("test_module", mock_module)
    
    @pytest.mark.asyncio
    async def test_event_emission(self, kernel):
        """Test event emission and handling."""
        await kernel._start_event_processor()
        
        handler_called = False
        
        def handler(payload):
            nonlocal handler_called
            handler_called = True
        
        kernel.register_event_handler(SecurityEvent.ANOMALY_DETECTED, handler)
        
        await kernel.emit_event(
            SecurityEvent.ANOMALY_DETECTED,
            "test_module",
            5,
            {"test": "data"}
        )
        
        # Give event processor time to process
        await asyncio.sleep(0.1)
        
        assert handler_called
    
    def test_health_check(self, kernel):
        """Test health check functionality."""
        health = kernel.health_check()
        
        assert "state" in health
        assert "registered_modules" in health
        assert "event_queue_size" in health
