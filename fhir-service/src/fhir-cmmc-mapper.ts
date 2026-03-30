/**
 * FHIR → CMMC Control Mapper
 * Maps FHIR R4 resource types and action codes to CMMC 2.0 control IDs.
 *
 * Healthcare DIB contractors must demonstrate that their FHIR-based systems
 * satisfy the same access-control, audit, and configuration controls required
 * by CMMC 2.0 / NIST SP 800-171 Rev 2.
 */

export interface FhirCmmcMapping {
  /** CMMC control IDs covered by this FHIR resource type */
  controlIds: string[];
  /** Zero-Trust pillar most closely associated */
  ztPillar: string;
  /** Human-readable rationale */
  rationale: string;
}

/**
 * Static mapping table from FHIR resource type to CMMC controls.
 * Extend this map as additional Implementation Guides are consumed.
 */
export const FHIR_CMMC_MAP: Record<string, FhirCmmcMapping> = {
  // ── Audit & Accountability ──────────────────────────────────────────────
  AuditEvent: {
    controlIds: [
      "AU.2.041", // Create and retain system audit logs
      "AU.2.042", // Ensure individual accountability
      "AU.2.043", // Review and analyze logs
      "AU.3.045", // Review/analyze/report audit log anomalies
      "AU.3.046", // Protect audit information from unauthorized access
      "AU.3.048", // Collect audit information into one/more central repositories
    ],
    ztPillar: "Visibility & Analytics",
    rationale:
      "FHIR AuditEvent resources are the healthcare-native mechanism for " +
      "recording who accessed what resource, when, and from where — directly " +
      "satisfying NIST AU-2/AU-3 requirements.",
  },

  DocumentReference: {
    controlIds: [
      "AU.3.046", // Protect audit logs
      "AU.3.048", // Central log repository
    ],
    ztPillar: "Visibility & Analytics",
    rationale:
      "DocumentReference resources that point to audit logs or policy " +
      "documents support audit-log retention and protection controls.",
  },

  // ── Access Control ──────────────────────────────────────────────────────
  Consent: {
    controlIds: [
      "AC.2.006", // Control the flow of CUI in accordance with approvals
      "AC.2.007", // Employ the principle of least privilege
      "AC.3.018", // Prevent non-privileged users from executing privileged functions
    ],
    ztPillar: "User",
    rationale:
      "FHIR Consent resources document patient-level access grants and " +
      "restrictions, which map to CMMC access-control and least-privilege " +
      "requirements for CUI.",
  },

  Patient: {
    controlIds: [
      "AC.1.001", // Limit system access to authorized users
      "AC.1.002", // Limit system access to types of transactions
    ],
    ztPillar: "User",
    rationale:
      "Patient resources carry the identity context required to enforce " +
      "authorized-access and transaction-type limitations.",
  },

  // ── Identification & Authentication ─────────────────────────────────────
  Practitioner: {
    controlIds: [
      "IA.1.076", // Identify information system users
      "IA.1.077", // Authenticate users before allowing access
      "IA.3.083", // Use multi-factor authentication for local and network access
    ],
    ztPillar: "User",
    rationale:
      "Practitioner resources carry the credential and role data needed to " +
      "verify identification and authentication of healthcare workforce " +
      "members accessing CUI.",
  },

  PractitionerRole: {
    controlIds: [
      "IA.1.076",
      "IA.1.077",
      "AC.2.007", // Least privilege — role-based
    ],
    ztPillar: "User",
    rationale:
      "PractitionerRole narrows access grants to a specific organizational " +
      "role, supporting least-privilege and identification controls.",
  },

  // ── Configuration Management ─────────────────────────────────────────────
  Device: {
    controlIds: [
      "CM.2.061", // Establish and maintain baseline configurations
      "CM.2.062", // Establish and maintain a software inventory
      "CM.3.068", // Restrict, disable, or prevent the use of nonessential programs
    ],
    ztPillar: "Device",
    rationale:
      "FHIR Device resources enumerate medical IoT endpoints that must " +
      "appear in the configuration baseline and software inventory.",
  },

  // ── Risk Assessment ──────────────────────────────────────────────────────
  Observation: {
    controlIds: [
      "RA.2.141", // Periodically assess risk to organizational operations
      "RA.2.142", // Scan for vulnerabilities in organizational systems
    ],
    ztPillar: "Visibility & Analytics",
    rationale:
      "Security-related Observation resources (e.g., vulnerability scan " +
      "results or anomaly flags) serve as machine-readable risk-assessment " +
      "artifacts.",
  },

  // ── System & Communications Protection ──────────────────────────────────
  Communication: {
    controlIds: [
      "SC.1.175", // Monitor communications at external boundaries
      "SC.1.176", // Implement subnetworks for publicly accessible components
      "SC.3.177", // Employ FIPS-validated cryptography
    ],
    ztPillar: "Network",
    rationale:
      "FHIR Communication resources record data-exchange events and can " +
      "evidence boundary-monitoring and encryption controls.",
  },

  // ── System & Information Integrity ───────────────────────────────────────
  OperationOutcome: {
    controlIds: [
      "SI.1.210", // Identify, report, and correct information system flaws
      "SI.1.211", // Provide protection from malicious code
    ],
    ztPillar: "Application",
    rationale:
      "OperationOutcome resources capture FHIR server error states and " +
      "validation failures, supporting flaw-identification requirements.",
  },
};

/** Resolve a FHIR resource type to its CMMC mapping (or undefined). */
export function getMappingForResourceType(
  resourceType: string
): FhirCmmcMapping | undefined {
  return FHIR_CMMC_MAP[resourceType];
}

/** Return all unique CMMC control IDs covered by a set of resource types. */
export function controlIdsForTypes(resourceTypes: string[]): string[] {
  const ids = new Set<string>();
  for (const rt of resourceTypes) {
    const mapping = FHIR_CMMC_MAP[rt];
    if (mapping) {
      for (const id of mapping.controlIds) {
        ids.add(id);
      }
    }
  }
  return [...ids].sort();
}
