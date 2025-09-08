def auth_headers_from_request(request) -> dict:
    """
    Constructs auth headers by checking for the token in cookies
    and then falling back to the Authorization header.
    """
    headers = {"Accept": "application/json"}
    
    # Try the cookie first, then the header.
    token = request.COOKIES.get("access_token") or request.headers.get("Authorization")

    if token:
        # Ensure the 'Bearer ' prefix is correctly formatted.
        if isinstance(token, str) and token.lower().startswith("bearer "):
            headers["Authorization"] = token
        else:
            headers["Authorization"] = f"Bearer {token}"
            
    return headers
