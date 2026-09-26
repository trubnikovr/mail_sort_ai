def normalize_database_url(database_url: str) -> str:
    """Select psycopg 3 for conventional PostgreSQL URLs."""
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url
