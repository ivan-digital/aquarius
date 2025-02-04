def store_token(token: str):
    """
    Store the token (e.g., writing to a file).
    Return a status string for display.
    """
    try:
        with open("my_token.txt", "w", encoding="utf-8") as f:
            f.write(token.strip())
        return "Token saved!"
    except Exception as e:
        return f"Error saving token: {str(e)}"