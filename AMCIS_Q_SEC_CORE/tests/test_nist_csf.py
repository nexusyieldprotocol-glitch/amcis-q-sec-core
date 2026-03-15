"""
Tests for NIST CSF 2.0 Implementation
======================================

Verifies completeness of control definitions and assessment engine.
"""

import json
import pytest
from pathlib import Path

from compliance.nist_csf import (
    CSFFunction,
    ImplementationStatus,
    RiskLevel,
    CSFControl,
    ControlEvidence,
    CSF_CONTROLS,
    NISTCSFEngine
)


class TestCSFFunctions:
    """Test CSF function definitions."""
    
    def test_all_functions_defined(self):
        """Verify all 6 CSF functions are defined."""
        expected = {"GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"}
        actual = {f.name for f in CSFFunction}
        assert actual == expected
    
    def test_function_codes(self):
        """Verify function codes match NIST standard."""
        assert CSFFunction.GOVERN.value == "GV"
        assert CSFFunction.IDENTIFY.value == "ID"
        assert CSFFunction.PROTECT.value == "PR"
        assert CSFFunction.DETECT.value == "DE"
        assert CSFFunction.RESPOND.value == "RS"
        assert CSFFunction.RECOVER.value == "RC"


class TestImplementationStatus:
    """Test implementation status enum."""
    
    def test_all_statuses_defined(self):
        """Verify all implementation statuses are defined."""
        expected = {
            "NOT_IMPLEMENTED",
            "PARTIALLY_IMPLEMENTED", 
            "IMPLEMENTED",
            "EXCEEDS_REQUIREMENTS",
            "NOT_APPLICABLE"
        }
        actual = {s.name for s in ImplementationStatus}
        assert actual == expected


class TestRiskLevel:
    """Test risk level enum."""
    
    def test_risk_level_values(self):
        """Verify risk level numeric values."""
        assert RiskLevel.MINIMAL.value == 0
        assert RiskLevel.LOW.value == 1
        assert RiskLevel.MODERATE.value == 2
        assert RiskLevel.HIGH.value == 3
        assert RiskLevel.CRITICAL.value == 4


class TestCSFControlsCompleteness:
    """Test that all CSF 2.0 controls are defined."""
    
    @pytest.fixture
    def controls(self):
        """Return CSF_CONTROLS dictionary."""
        return CSF_CONTROLS
    
    def test_govern_controls(self, controls):
        """Verify GOVERN function controls."""
        govern_controls = [k for k in controls.keys() if k.startswith("GV.")]
        expected = ["GV.OC", "GV.RM", "GV.RR", "GV.PO", "GV.OV", "GV.SC"]
        assert sorted(govern_controls) == sorted(expected)
    
    def test_identify_controls(self, controls):
        """Verify IDENTIFY function controls."""
        identify_controls = [k for k in controls.keys() if k.startswith("ID.")]
        expected = ["ID.AM", "ID.RA", "ID.IM"]
        assert sorted(identify_controls) == sorted(expected)
    
    def test_protect_controls(self, controls):
        """Verify PROTECT function controls."""
        protect_controls = [k for k in controls.keys() if k.startswith("PR.")]
        expected = ["PR.AA", "PR.AT", "PR.DS", "PR.PS", "PR.IR"]
        assert sorted(protect_controls) == sorted(expected)
    
    def test_detect_controls(self, controls):
        """Verify DETECT function controls."""
        detect_controls = [k for k in controls.keys() if k.startswith("DE.")]
        expected = ["DE.AE", "DE.CM", "DE.IM"]
        assert sorted(detect_controls) == sorted(expected)
    
    def test_respond_controls(self, controls):
        """Verify RESPOND function controls."""
        respond_controls = [k for k in controls.keys() if k.startswith("RS.")]
        expected = ["RS.MA", "RS.AN", "RS.CO", "RS.MI", "RS.IM"]
        assert sorted(respond_controls) == sorted(expected)
    
    def test_recover_controls(self, controls):
        """Verify RECOVER function controls."""
        recover_controls = [k for k in controls.keys() if k.startswith("RC.")]
        expected = ["RC.RP", "RC.IM", "RC.CO"]
        assert sorted(recover_controls) == sorted(expected)
    
    def test_total_control_count(self, controls):
        """Verify total control count matches NIST CSF 2.0."""
        assert len(controls) == 23
    
    def test_all_controls_have_required_fields(self, controls):
        """Verify all controls have required fields."""
        required_fields = ["function", "category", "description", "examples", "modules", "priority"]
        for control_id, config in controls.items():
            for field in required_fields:
                assert field in config, f"Control {control_id} missing field: {field}"


class TestNISTCSFEngine:
    """Test NIST CSF assessment engine."""
    
    @pytest.fixture
    def engine(self):
        """Create NIST CSF engine instance."""
        return NISTCSFEngine()
    
    def test_engine_loads_all_controls(self, engine):
        """Verify engine loads all controls."""
        assert len(engine.controls) == 23
    
    def test_engine_loads_correct_control_types(self, engine):
        """Verify engine loads controls as CSFControl instances."""
        for control_id, control in engine.controls.items():
            assert isinstance(control, CSFControl)
            assert control.control_id == control_id
    
    def test_assess_control_invalid_id(self, engine):
        """Test assessing invalid control ID."""
        with pytest.raises(ValueError, match="Unknown control"):
            engine.assess_control("INVALID.ID")
    
    def test_determine_status_no_evidence(self, engine):
        """Test status determination with no evidence."""
        control = CSFControl(
            control_id="TEST.01",
            function=CSFFunction.GOVERN,
            category="Test",
            subcategory="TEST.01",
            description="Test control",
            implementation_examples=[],
            amcis_modules=[]
        )
        status = engine._determine_status(control)
        assert status == ImplementationStatus.NOT_IMPLEMENTED


class TestJSONExport:
    """Test JSON export functionality."""
    
    def test_json_file_exists(self):
        """Verify csf_controls.json file exists."""
        json_path = Path(__file__).parent.parent / "compliance" / "csf_controls.json"
        assert json_path.exists(), "csf_controls.json not found"
    
    def test_json_file_valid(self):
        """Verify csf_controls.json is valid JSON."""
        json_path = Path(__file__).parent.parent / "compliance" / "csf_controls.json"
        with open(json_path) as f:
            data = json.load(f)
        assert data is not None
    
    def test_json_has_all_functions(self):
        """Verify JSON contains all 6 CSF functions."""
        json_path = Path(__file__).parent.parent / "compliance" / "csf_controls.json"
        with open(json_path) as f:
            data = json.load(f)
        
        expected_functions = {"GOVERN", "IDENTIFY", "PROTECT", "DETECT", "RESPOND", "RECOVER"}
        actual_functions = set(data["functions"].keys())
        assert actual_functions == expected_functions
    
    def test_json_control_count_matches(self):
        """Verify JSON control count matches Python definitions."""
        json_path = Path(__file__).parent.parent / "compliance" / "csf_controls.json"
        with open(json_path) as f:
            data = json.load(f)
        
        total_controls = sum(f["control_count"] for f in data["functions"].values())
        assert total_controls == len(CSF_CONTROLS)


class TestControlEvidence:
    """Test control evidence handling."""
    
    def test_evidence_creation(self):
        """Test creating control evidence."""
        from datetime import datetime
        
        evidence = ControlEvidence(
            evidence_id="test-evidence-001",
            control_id="PR.DS",
            evidence_type="policy",
            source="/policies/data-security.pdf",
            timestamp=datetime.now(),
            description="Data security policy document",
            data_hash="a1b2c3d4e5f6"
        )
        
        assert evidence.control_id == "PR.DS"
        assert evidence.evidence_type == "policy"
    
    def test_evidence_immutability(self):
        """Test that evidence is immutable."""
        from datetime import datetime
        
        evidence = ControlEvidence(
            evidence_id="test-evidence-001",
            control_id="PR.DS",
            evidence_type="policy",
            source="/policies/data-security.pdf",
            timestamp=datetime.now(),
            description="Data security policy document",
            data_hash="a1b2c3d4e5f6"
        )
        
        # Should not be able to modify frozen dataclass
        with pytest.raises(AttributeError):
            evidence.control_id = "NEW.ID"


class TestCSFControl:
    """Test CSF Control dataclass."""
    
    def test_control_creation(self):
        """Test creating CSF control."""
        control = CSFControl(
            control_id="PR.DS",
            function=CSFFunction.PROTECT,
            category="Data Security",
            subcategory="PR.DS",
            description="Data is managed and protected",
            implementation_examples=["Data classification", "Encryption"],
            amcis_modules=["amcis_encrypt", "dlp_engine"]
        )
        
        assert control.control_id == "PR.DS"
        assert control.function == CSFFunction.PROTECT
        assert control.priority == RiskLevel.MODERATE  # Default
    
    def test_control_to_dict(self):
        """Test control serialization."""
        control = CSFControl(
            control_id="PR.DS",
            function=CSFFunction.PROTECT,
            category="Data Security",
            subcategory="PR.DS",
            description="Data is managed and protected",
            implementation_examples=["Data classification"],
            amcis_modules=["amcis_encrypt"]
        )
        
        data = control.to_dict()
        assert data["control_id"] == "PR.DS"
        assert data["function"] == "PROTECT"
        assert "score" in data
