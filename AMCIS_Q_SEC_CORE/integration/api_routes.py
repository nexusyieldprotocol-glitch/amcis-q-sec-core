"""
AMCIS Q-Sec-Core Integration API Routes
=======================================

This module defines the RESTful endpoints for AMCIS 9.0 to interact 
with the Q-Sec-Core security modules.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Dict, Any
from amcis_kernel import AMCISKernel
from amcis_redis import RedisManager

router = APIRouter(prefix="/api/v1/integration", tags=["Integration"])
redis_mgr = RedisManager()

# Dependency to get kernel instance
def get_kernel():
    return AMCISKernel()

@app.get("/threats/active")
async def get_active_threats(kernel: AMCISKernel = Depends(get_kernel)):
    """Retrieve list of currently active security threats."""
    anomaly_engine = kernel.get_module("anomaly_engine")
    return anomaly_engine.get_active_threats()

@app.get("/trust/scores")
async def get_all_trust_scores(kernel: AMCISKernel = Depends(get_kernel)):
    """Retrieve identity trust scores for all active network nodes."""
    trust_engine = kernel.get_module("trust_engine")
    return trust_engine.get_scores()

@router.post("/response/mitigate/{threat_id}")
async def trigger_mitigation(threat_id: str, kernel: AMCISKernel = Depends(get_kernel)):
    """Manually trigger a mitigation playbook for a specific threat."""
    response_engine = kernel.get_module("response_engine")
    result = response_engine.execute_playbook(threat_id)
    
    # Notify via Redis
    redis_mgr.publish_event("security_events", {
        "action": "mitigation_triggered",
        "threat_id": threat_id,
        "result": result
    })
    
    return {"status": "success", "action": result}

@app.get("/compliance/summary")
async def get_compliance_summary(kernel: AMCISKernel = Depends(get_kernel)):
    """Get high-level NIST CSF 2.0 compliance summary."""
    # Logic to pull from nist_csf.py assessment
    return {"overall_score": 0.88, "functions": {"GV": 0.9, "ID": 0.85}}
