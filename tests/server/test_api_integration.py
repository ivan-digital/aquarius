import pytest
import requests
import os
from typing import Generator
from testcontainers.compose import DockerCompose
import time
import docker

# Use a fixed path for the docker-compose file
COMPOSE_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../docker-compose.app.yml"))

@pytest.fixture(scope="module")
def api_service(docker_client: docker.client.DockerClient) -> Generator[DockerCompose, None, None]:
    """
    Pytest fixture to start and stop the API service using Docker Compose.
    """
    compose_file_dir = os.path.dirname(COMPOSE_FILE_PATH)
    compose_file_name = os.path.basename(COMPOSE_FILE_PATH)

    if not os.path.exists(COMPOSE_FILE_PATH):
        pytest.fail(f"Docker Compose file not found at {COMPOSE_FILE_PATH}")

    compose = DockerCompose(
        compose_file_dir,
        compose_file_name=compose_file_name,
        pull=True,
        services=['api']
    )

    def _wait_for_api_log(container_obj, log_pattern_str: str, timeout_seconds: int = 120):
        """Polls container logs for a specific regex pattern."""
        container_name = getattr(container_obj, 'name', str(container_obj))
        print(f"Waiting for log pattern '{log_pattern_str}' in container {container_name} for {timeout_seconds}s...")
        import re
        compiled_pattern = re.compile(log_pattern_str)
        start_time = time.monotonic()
        last_logs_checked = ""

        container_id_available_timeout = 30
        id_wait_start_time = time.monotonic()
        while not (hasattr(container_obj, 'ID') and container_obj.ID):
            if time.monotonic() - id_wait_start_time > container_id_available_timeout:
                pytest.fail(f"Timeout waiting for container ID for {container_name} after {container_id_available_timeout}s.")
            print(f"Container {container_name} has no ID yet, waiting...")
            time.sleep(1)
        
        print(f"Container {container_name} ID is {container_obj.ID}. Proceeding to fetch logs.")

        while time.monotonic() - start_time < timeout_seconds:
            print(f"Polling logs for {container_name} (elapsed: {time.monotonic() - start_time:.2f}s)...") # ADDED: Polling indicator
            try:
                raw_logs = docker_client.api.logs(container_obj.ID, stream=False, timestamps=True)
                current_logs = raw_logs.decode('utf-8', errors='replace')
                last_logs_checked = current_logs
                if compiled_pattern.search(current_logs):
                    print(f"Pattern '{log_pattern_str}' found in logs for {container_name}.")
                    # ADDED: Print matching part of the log
                    match = compiled_pattern.search(current_logs)
                    if match:
                        # Print a snippet around the match
                        context_chars = 100
                        start_index = max(0, match.start() - context_chars)
                        end_index = min(len(current_logs), match.end() + context_chars)
                        print(f"Matching log snippet: ...{current_logs[start_index:end_index]}...")
                    return
            except docker.errors.NotFound:
                print(f"Container {container_name} (ID: {container_obj.ID}) not found by Docker API.")
            except Exception as e:
                print(f"Error fetching logs for {container_name} (ID: {getattr(container_obj, 'ID', 'N/A')}): {e}")
            time.sleep(2) 
        
        print(f"Timeout waiting for log pattern '{log_pattern_str}' in {container_name} after {timeout_seconds}s.")
        try:
            print(f"--- Full logs for {container_name} on timeout ---")
            all_raw_logs = docker_client.api.logs(container_obj.ID, stream=False, timestamps=True, tail=1000) # Get last 1000 lines
            all_logs_decoded = all_raw_logs.decode('utf-8', errors='replace')
            print(all_logs_decoded)
            print(f"--- End full logs for {container_name} ---")
        except Exception as e_logs:
            print(f"Could not fetch full logs on timeout: {e_logs}")
            log_snippet_length = 2000 # Increased snippet length
            log_snippet = last_logs_checked[-log_snippet_length:]
            pytest.fail(f"Timeout waiting for log pattern '{log_pattern_str}' in {container_name}. Last log snippet ({log_snippet_length} chars):\\n{log_snippet}")

        pytest.fail(f"Timeout waiting for log pattern '{log_pattern_str}' in {container_name} after {timeout_seconds}s. Check printed full logs.")

    try:
        print("Attempting to start Docker Compose API service...")
        compose.start()
        print("Docker Compose API service starting...")

        api_container = compose.get_container("api")
        print(f"Waiting for API service (container: {getattr(api_container, 'name', 'N/A')} ID: {getattr(api_container, 'id', 'N/A')})...")
        # _wait_for_api_log(api_container, r"Uvicorn running on|Application startup complete.", timeout_seconds=180) # Original Uvicorn/FastAPI pattern
        _wait_for_api_log(api_container, r"Running on http://0\.0\.0\.0:5001/", timeout_seconds=180) # Flask dev server pattern
        print("API service is ready.")
        
        time.sleep(5)

        yield compose
    finally:
        print("Stopping Docker Compose API service...")
        if compose:
            compose.stop()
        print("Docker Compose API service stopped.")


def test_api_chat_endpoint(api_service: DockerCompose):
    """
    Test the /chat endpoint of the API.
    """
    api_url = "http://localhost:5001/chat"  # MODIFIED: Changed port from 8000 to 5001
    payload = {
        "user_id": "test_user",
        "query": "Hello, world!",
        "context": "Test context"
    }
    headers = {"Content-Type": "application/json"}

    print(f"Sending POST request to {api_url} with payload: {payload}")
    response = requests.post(api_url, json=payload, headers=headers)
    print(f"Response status code: {response.status_code}")
    
    # Print the JSON response
    try:
        response_json = response.json()
        print(f"Response JSON: {response_json}")
    except requests.exceptions.JSONDecodeError:
        print(f"Response content (not JSON): {response.text}")

    assert response.status_code == 200, f"Expected status 200 OK, got {response.status_code}. Response: {response.text}"


def test_api_health_check_placeholder(api_service: DockerCompose):
    """
    Placeholder for a potential health check endpoint.
    If /health does not exist, this test will fail, indicating it might need to be created.
    """
    base_url = "http://localhost:5001"
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10) # MODIFIED: Changed /health to /api/health
        assert response.status_code == 200, f"Health check endpoint /api/health failed or does not exist. Status: {response.status_code}" # MODIFIED: Changed /health to /api/health
        data = response.json()
        assert data.get("status") == "healthy", f"Health check response did not contain 'status: healthy'. Response: {data}"
        print("Health check successful.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request to /api/health endpoint failed: {e}") # MODIFIED: Changed /health to /api/health

