from starlette.requests import Request


def get_client_ip(request: Request) -> str:
    """Extract real client IP considering reverse proxy headers (X-Forwarded-For, CF-Connecting-IP)."""
    cf_connecting_ip = request.headers.get("CF-Connecting-IP")
    if cf_connecting_ip:
        return cf_connecting_ip.strip()

    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"
