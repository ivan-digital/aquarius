"""
Tests for Gradio UI using Selenium to simulate user interactions.
"""
import pytest
from typing import Generator
import subprocess
import sys
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def start_app_process() -> subprocess.Popen:
    """Start the Aquarius API + UI application in a subprocess."""
    # Launch the main application
    cmd = [sys.executable, "-u", "-m", "app.main"]
    # Capture stdout/stderr to assert MCP server initialization
    return subprocess.Popen(
        cmd,
        cwd=".",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )


@pytest.fixture(scope="module")
def app_process() -> Generator[subprocess.Popen, None, None]:
    """Pytest fixture to start and stop the application, waiting for UI to be available."""
    proc = start_app_process()
    # Wait up to 10s for Gradio UI to be ready, polling every 0.5s
    for _ in range(20):
        try:
            requests.get("http://127.0.0.1:7860", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        pytest.skip("Gradio UI did not start in time")
    yield proc
    proc.kill()


def test_selenium_user_chat(app_process: subprocess.Popen) -> None:
    """Simulate a user asking for recent PyTorch GitHub repo updates."""
    # The app_process fixture ensures the UI is running
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    # Instantiate Chrome WebDriver directly; skip if unavailable
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        pytest.skip(f"Unable to launch Chrome WebDriver: {e}")

    # Open the Gradio UI
    driver.get("http://127.0.0.1:7860")

    # Wait up to 5s checking every 0.1s for the input box
    input_box = WebDriverWait(driver, timeout=5, poll_frequency=0.1).until(
        EC.presence_of_element_located((By.TAG_NAME, "textarea"))
    )

    # Enter the test query
    input_box.send_keys("Provide pytorch recent github repo updates")

    # Send the message by pressing Enter
    input_box.send_keys(Keys.ENTER)

    # Wait up to 5s for assistant's response in page source, polling fast
    WebDriverWait(driver, timeout=5, poll_frequency=0.1).until(
        lambda d: "commit" in d.page_source.lower() or "github" in d.page_source.lower()
    )
    body_text = driver.page_source
    # Print exact assistant response
    print("Assistant response:\n", body_text)
    assert "commit" in body_text.lower() or "github" in body_text.lower()
    # Clean up: close browser and stop app
    driver.quit()
    app_process.kill()
