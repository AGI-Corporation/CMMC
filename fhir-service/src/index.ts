/**
 * BabelFHIR-TS Validation Sidecar — Express Server
 * AGI Corporation 2026
 *
 * Exposes a single POST /validate endpoint that the Python CMMC backend
 * calls (via FHIR_VALIDATOR_URL) to validate FHIR R4 resources before they
 * are ingested as compliance evidence.
 *
 * Start:
 *   PORT=3100 npm start
 *
 * Docker:
 *   docker build -t cmmc-fhir-service .
 *   docker run -p 3100:3100 cmmc-fhir-service
 */

import express, { Request, Response } from "express";
import { FhirValidator } from "./fhir-validator";
import { getMappingForResourceType } from "./fhir-cmmc-mapper";

const app = express();
app.use(express.json({ type: ["application/json", "application/fhir+json"] }));

const PORT = parseInt(process.env.PORT ?? "3100", 10);
const FHIR_BASE_URL = process.env.FHIR_BASE_URL ?? "http://localhost:8080/fhir";

const validator = new FhirValidator(FHIR_BASE_URL);

// ─── Health check ─────────────────────────────────────────────────────────────

app.get("/health", (_req: Request, res: Response) => {
  res.json({ status: "ok", service: "cmmc-fhir-validator" });
});

// ─── POST /validate ───────────────────────────────────────────────────────────

/**
 * Validate a FHIR R4 resource.
 *
 * Request body: any FHIR R4 resource JSON.
 * Response 200: { valid, warnings, resourceType, cmmcMapping }
 * Response 422: { valid: false, errors, resourceType }
 */
app.post("/validate", async (req: Request, res: Response) => {
  const resource = req.body as Record<string, unknown>;

  if (!resource || typeof resource !== "object") {
    res.status(400).json({ error: "Request body must be a FHIR resource JSON object." });
    return;
  }

  const result = await validator.validate(resource);
  const resourceType = result.resourceType;
  const cmmcMapping = getMappingForResourceType(resourceType) ?? null;

  if (!result.valid) {
    res.status(422).json({
      valid: false,
      errors: result.errors,
      warnings: result.warnings,
      resourceType,
      cmmcMapping,
    });
    return;
  }

  res.status(200).json({
    valid: true,
    warnings: result.warnings,
    resourceType,
    resourceId: result.resourceId,
    cmmcMapping,
  });
});

// ─── GET /mappings ────────────────────────────────────────────────────────────

/**
 * List all supported FHIR resource types and their CMMC control mappings.
 * Mirrors the Python backend's GET /api/fhir/mappings for sidecar clients.
 */
app.get("/mappings", (_req: Request, res: Response) => {
  // Dynamically import the full map to avoid duplication
  const { FHIR_CMMC_MAP } = require("./fhir-cmmc-mapper");
  res.json(FHIR_CMMC_MAP);
});

// ─── Start ────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`[cmmc-fhir-service] BabelFHIR-TS validator listening on :${PORT}`);
  console.log(`[cmmc-fhir-service] FHIR base URL: ${FHIR_BASE_URL}`);
});

export default app;
