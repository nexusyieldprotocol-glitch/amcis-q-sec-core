"""
Tests for EDR modules.
"""

import pytest
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from edr.amcis_process_graph import (
    ProcessGraph, ProcessNode, ProcessState, ProcessAnomalyType
)
from edr.amcis_memory_inspector import (
    MemoryInspector, MemoryRegion, MemoryProtection, MemoryRegionType
)


class TestProcessGraph:
    """Test cases for ProcessGraph."""
    
    @pytest.fixture
    def graph(self):
        """Create a process graph instance."""
        return ProcessGraph(scan_interval=5.0)
    
    def test_scan_processes(self, graph):
        """Test process scanning."""
        processes = graph.scan_processes()
        
        # Should return a dictionary
        assert isinstance(processes, dict)
        # Should find at least one process (ourselves)
        assert len(processes) > 0
    
    def test_update_graph(self, graph):
        """Test graph update."""
        processes = graph.update_graph()
        
        assert isinstance(processes, dict)
        # Should have stored processes
        assert len(graph._processes) > 0
    
    def test_get_process_lineage(self, graph):
        """Test lineage retrieval."""
        # Update graph first
        graph.update_graph()
        
        # Get own PID
        import os
        own_pid = os.getpid()
        
        lineage = graph.get_process_lineage(own_pid)
        
        # Should return a list
        assert isinstance(lineage, list)
        # First element should be the requested process
        if lineage:
            assert lineage[0].pid == own_pid


class TestMemoryInspector:
    """Test cases for MemoryInspector."""
    
    @pytest.fixture
    def inspector(self):
        """Create a memory inspector instance."""
        return MemoryInspector()
    
    def test_calculate_entropy(self, inspector):
        """Test entropy calculation."""
        # High entropy data
        high_entropy = b"\x00\xff" * 100
        entropy = inspector._calculate_entropy(high_entropy)
        assert 0 <= entropy <= 8
        
        # Low entropy data
        low_entropy = b"\x00" * 200
        entropy = inspector._calculate_entropy(low_entropy)
        assert entropy < 1.0
    
    def test_analyze_region(self, inspector):
        """Test region analysis."""
        region = MemoryRegion(
            start_address=0x1000,
            end_address=0x2000,
            size=0x1000,
            protection={MemoryProtection.READ, MemoryProtection.WRITE},
            region_type=MemoryRegionType.HEAP,
            is_rwx=False,
            is_writable_executable=False
        )
        
        # Just verify no exceptions
        inspector._analyze_region(region, 1234)
    
    def test_get_memory_map(self, inspector):
        """Test memory map retrieval."""
        import os
        own_pid = os.getpid()
        
        regions = inspector._get_memory_map(own_pid)
        
        # Should return a list
        assert isinstance(regions, list)


class TestFileIntegrityMonitor:
    """Test cases for FileIntegrityMonitor."""
    
    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a file integrity monitor."""
        from AMCIS_Q_SEC_CORE.edr.amcis_file_integrity import FileIntegrityMonitor
        return FileIntegrityMonitor(baseline_path=tmp_path / "baseline.json")
    
    def test_establish_baseline(self, monitor, tmp_path):
        """Test baseline establishment."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        count = monitor.establish_baseline([str(test_file)])
        
        assert count == 1
        assert str(test_file) in monitor._baselines
    
    def test_verify_file(self, monitor, tmp_path):
        """Test file verification."""
        # Create and baseline a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        monitor.establish_baseline([str(test_file)])
        
        # Verify unchanged file
        valid, error = monitor.verify_file(str(test_file))
        assert valid is True
        assert error is None
        
        # Modify file
        test_file.write_text("modified content")
        
        # Verify should fail
        valid, error = monitor.verify_file(str(test_file))
        assert valid is False
        assert error is not None
