## 2026-05-20 - Fix Information Exposure in Mistral Agent Endpoints
**Vulnerability:** Fast API routes in `agents/mistral_agent/agent.py` were returning `str(e)` directly inside a 500 HTTP Exception (`raise HTTPException(status_code=500, detail=str(e))`).
**Learning:** Returning `str(e)` from broad Exception catches leaks server-side internals, such as database query structures or upstream API errors to the client, leading to a CWE-209 Information Exposure vulnerability.
**Prevention:** Catch the exceptions, log the full stack trace server-side using `logging.error(..., exc_info=True)`, and return a generic safe error message to the client.
