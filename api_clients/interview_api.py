import json
from urllib import request


DEFAULT_TIMEOUT = 15


def post_interview_seed(endpoint, seed, api_key="", timeout=DEFAULT_TIMEOUT):
    """Send the generated interview seed to a future interview API endpoint."""
    body = json.dumps(seed, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = request.Request(endpoint, data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        response_body = response.read().decode("utf-8")
        if not response_body:
            return {}
        return json.loads(response_body)
