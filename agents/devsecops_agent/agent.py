"""
DevSecOps Agent - ZT Application Pillar
AGI Corporation 2026

Aligns with CMMC CM/SI domains, Fulcrum LOE 2, Cloud Security Playbook Play 19-21.
Responsibilities: container scanning, SBOM generation, pipeline gate evaluation.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from fastapi import APIRouter


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PASS = "pass"


class DevSecOpsAgent:
    APPROVED_BASE_IMAGES = [
        "registry.access.redhat.com/ubi9/ubi-minimal",
        "gcr.io/distroless/python3",
        "cgr.dev/chainguard/python",
    ]

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

    def scan_container_image(self, image_name: str, image_tag: str = "latest",
                              base_image: Optional[str] = None) -> Dict[str, Any]:
        """Simulate CVE scan. Production: Trivy/Grype. Maps to NIST 800-190, CMMC SI.1.210."""
        cves = [
            {"cve_id": "CVE-2024-1234", "severity": "high", "package": "openssl",
             "version": "3.0.1", "fixed_in": "3.0.2", "cmmc_controls": ["SI.1.210", "SI.2.214"]}
        ] if "vulnerable" in image_name else []
        return {
            "image": f"{image_name}:{image_tag}",
            "base_image": base_image,
            "base_image_approved": base_image in self.APPROVED_BASE_IMAGES,
            "overall_risk": "pass" if not cves else "high",
            "cve_findings": cves,
            "critical_count": 0, "high_count": len(cves),
            "evidence_id": str(uuid.uuid4()),
            "scanned_at": datetime.utcnow().isoformat(),
            "cmmc_controls": ["SI.1.210", "SI.2.214", "CM.2.061", "CM.3.068"],
            "zt_pillar": "Application",
        }

    def generate_sbom(self, service_name: str) -> Dict[str, Any]:
        """Generate CycloneDX SBOM. Maps to EO 14028, CMMC CM.2.062."""
        components = [
            {"name": "fastapi", "version": "0.111.0", "license": "MIT",
             "supplier": "tiangolo", "cves": 0},
            {"name": "mistralai", "version": "0.4.2", "license": "Apache-2.0",
             "supplier": "Mistral AI", "cves": 0},
            {"name": "sqlalchemy", "version": "2.0.30", "license": "MIT",
             "supplier": "SQLAlchemy", "cves": 0},
            {"name": "pydantic", "version": "2.7.0", "license": "MIT",
             "supplier": "pydantic", "cves": 0},
        ]
        return {
            "sbom_format": "CycloneDX-1.5",
            "service": service_name,
            "component_count": len(components),
            "high_risk_components": 0,
            "components": components,
            "evidence_id": str(uuid.uuid4()),
            "generated_at": datetime.utcnow().isoformat(),
            "cmmc_controls": ["CM.2.061", "CM.2.062", "SI.2.214"],
            "zt_pillar": "Application",
        }

    def evaluate_pipeline_gates(self, pipeline_id: str) -> Dict[str, Any]:
        """Evaluate CI/CD security gates. Maps to Cloud Security Playbook Play 20."""
        gate_results = {
            "sast": "pass", "secret_scan": "pass", "dependency_check": "warn",
            "container_scan": "pass", "sbom_generation": "pass", "image_signing": "fail",
        }
        failed = [g for g, s in gate_results.items() if s == "fail"]
        warned = [g for g, s in gate_results.items() if s == "warn"]
        confidence = max(0.0, 1.0 - len(failed) * 0.2 - len(warned) * 0.05)
        return {
            "pipeline_id": pipeline_id,
            "gates_total": len(gate_results),
            "gates_passed": len([s for s in gate_results.values() if s == "pass"]),
            "gates_failed": len(failed),
            "failed_gates": failed,
            "warned_gates": warned,
            "overall_status": "fail" if failed else "pass",
            "confidence_score": round(confidence, 2),
            "gate_details": [{"gate": g, "status": s} for g, s in gate_results.items()],
            "cmmc_controls": ["CM.2.061", "SI.1.210", "SI.2.214", "CM.3.068"],
            "zt_pillar": "Application",
            "evidence_id": str(uuid.uuid4()),
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    def run_full_assessment(self, service_name: str = "cmmc-api") -> Dict[str, Any]:
        """Run complete DevSecOps assessment pipeline."""
        image_scan = self.scan_container_image(service_name)
        sbom = self.generate_sbom(service_name)
        pipeline = self.evaluate_pipeline_gates(f"{service_name}-pipeline")
        confidence = (
            (1.0 if image_scan["overall_risk"] == "pass" else 0.5) * 0.4
            + pipeline["confidence_score"] * 0.4
            + (1.0 if sbom["high_risk_components"] == 0 else 0.7) * 0.2
        )
        return {
            "agent": "devsecops",
            "service": service_name,
            "zt_pillar": "Application",
            "overall_confidence": round(confidence, 2),
            "image_scan": image_scan,
            "sbom": sbom,
            "pipeline_gates": pipeline,
            "timestamp": datetime.utcnow().isoformat(),
        }


router = APIRouter()
_dso = DevSecOpsAgent()


@router.get("/assess/{service_name}", summary="Run full DevSecOps ZT Application assessment")
async def assess_service(service_name: str):
    """Container scan + SBOM + pipeline gates - ZT Application Pillar evidence."""
    return _dso.run_full_assessment(service_name)


@router.post("/scan-image", summary="Scan container image for CVEs")
async def scan_image(image_name: str, image_tag: str = "latest", base_image: str = ""):
    """CVE scan mapped to NIST 800-190 and CMMC SI/CM controls."""
    return _dso.scan_container_image(image_name, image_tag, base_image or None)


@router.get("/sbom/{service_name}", summary="Generate CycloneDX SBOM")
async def get_sbom(service_name: str):
    """SBOM generation mapped to EO 14028 and CMMC CM.2.062."""
    return _dso.generate_sbom(service_name)
