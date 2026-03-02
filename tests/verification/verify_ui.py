
from playwright.sync_api import sync_playwright, expect
import time
import subprocess
import os
import signal

def verify_frontend():
    # Start backend
    backend_proc = subprocess.Popen(["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Start frontend
    os.environ["VITE_API_URL"] = "http://localhost:8000"
    frontend_proc = subprocess.Popen(["npm", "run", "dev", "--", "--host", "0.0.0.0"],
                                      cwd="frontend",
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(15) # Increased wait

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # 1. Dashboard
            page.goto("http://localhost:5173")
            # Wait for either the summary or a fallback if no data
            page.wait_for_selector("text=SPRS Score", timeout=30000)
            page.screenshot(path="tests/verification/dashboard.png")
            print("Captured Dashboard")

            # 2. Controls Page
            page.get_by_role("link", name="Controls").click()
            page.wait_for_selector("td", timeout=30000) # Wait for table data
            page.screenshot(path="tests/verification/controls_page.png")
            print("Captured Controls Page")

            # 3. Evidence Page
            page.get_by_role("link", name="Evidence").click()
            # Wait for content or "No evidence" message
            page.wait_for_selector("text=Evidence Vault", timeout=30000)
            time.sleep(2)
            page.screenshot(path="tests/verification/evidence_page.png")
            print("Captured Evidence Page")

            # 4. Reports Page
            page.get_by_role("link", name="Reports").click()
            page.wait_for_selector("text=Report Center", timeout=30000)
            page.screenshot(path="tests/verification/reports_page.png")
            print("Captured Reports Page")

            # 5. Agents Page
            page.get_by_role("link", name="Agents").click()
            page.wait_for_selector("text=NANDA-registered", timeout=30000)
            page.screenshot(path="tests/verification/agents_page.png")
            print("Captured Agents Page")

            browser.close()
    finally:
        os.kill(backend_proc.pid, signal.SIGTERM)
        os.kill(frontend_proc.pid, signal.SIGTERM)

if __name__ == "__main__":
    verify_frontend()
