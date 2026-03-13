## 2026-02-26 - Trusting Agent Findings without Validation
**Vulnerability:** The 'promote_agent_run' endpoint allowed raw JSON findings from AI agents to be persisted directly as official assessment records without validating that confidence scores were in [0.0, 1.0] or that statuses matched allowed enums.
**Learning:** Architectures that use AI agents to automate data entry often neglect input validation for the data produced by the agents, mistakenly assuming that "internal" AI output is inherently safe or follows schema constraints.
**Prevention:** Implement strict schema validation or clamping logic at the boundary where agent findings are "promoted" to official system records, treating agent-generated data as untrusted user input.
