import pytest
import docker
import docker.client

def test_docker_client_fixture_availability(docker_client: docker.client.DockerClient):
    """
    Tests if the docker_client fixture is available and is of the correct type.
    """
    assert docker_client is not None, "docker_client fixture is None"
    assert isinstance(docker_client, docker.client.DockerClient), \
        f"docker_client is not a DockerClient instance, got {type(docker_client)}"
    try:
        client_info = docker_client.info()
        assert "ID" in client_info, "Docker client .info() call failed or returned unexpected data"
        print(f"Successfully retrieved Docker info using docker_client: {client_info.get('Name')}")
    except docker.errors.DockerException as e:
        pytest.fail(f"docker_client.info() raised an exception: {e}")
