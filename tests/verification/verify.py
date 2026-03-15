import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Test CMMC
        await page.goto("http://localhost:5173")
        await page.wait_for_selector("h1")
        await page.screenshot(path="tests/verification/cmmc.png")
        print("CMMC Screenshot taken")

        # Switch to HIPAA
        await page.select_option("select", "HIPAA")
        await page.wait_for_timeout(2000)
        await page.screenshot(path="tests/verification/hipaa.png")
        print("HIPAA Screenshot taken")

        # Check if "HIPAA Control Explorer" is visible
        explorer_text = await page.inner_text("h3")
        print(f"Explorer title: {explorer_text}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
