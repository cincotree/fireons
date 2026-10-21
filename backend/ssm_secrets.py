import os
from collections.abc import MutableMapping
from typing import Any


def _parameter_env_name(parameter_name: str) -> str:
    return parameter_name.rsplit("/", 1)[-1]


def load_ssm_parameters(
    prefix: str | None = None,
    client: Any = None,
    environ: MutableMapping[str, str] = os.environ,
) -> list[str]:
    if prefix is None:
        prefix = environ.get("SSM_PREFIX", "")
    prefix = prefix.strip()
    if not prefix:
        return []

    if client is None:
        import boto3

        client = boto3.client("ssm")

    path = "/" + prefix.strip("/")
    loaded: list[str] = []
    next_token = None
    while True:
        request: dict[str, Any] = {"Path": path, "Recursive": False, "WithDecryption": True}
        if next_token:
            request["NextToken"] = next_token
        response = client.get_parameters_by_path(**request)
        for parameter in response.get("Parameters", []):
            env_name = _parameter_env_name(parameter["Name"])
            if env_name and env_name not in environ:
                environ[env_name] = parameter["Value"]
                loaded.append(env_name)
        next_token = response.get("NextToken")
        if not next_token:
            break

    print(f"Loaded {len(loaded)} parameters from SSM path {path}")
    return loaded
