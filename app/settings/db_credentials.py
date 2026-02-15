# qdrant_host="localhost"
# qdrant_port=6333
# qdrant_collection_name = "content_chunks"


# postgres_host = "localhost"
# postgres_port = 5432
# postgres_db = "myapp_db"
# postgres_user = "myapp"
# postgres_password = "mysecretpassword"



import os

# Настройки Qdrant
qdrant_host = os.environ.get("QDRANT_HOST", "localhost")
qdrant_port = int(os.environ.get("QDRANT_PORT", 6333))
qdrant_collection_name = os.environ.get("QDRANT_COLLECTION_NAME", "content_chunks")


# Настройки PostgreSQL
postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
postgres_port = int(os.environ.get("POSTGRES_PORT", 5432))
postgres_db = os.environ.get("POSTGRES_DB", "myapp_db")
postgres_user = os.environ.get("POSTGRES_USER", "myapp")
postgres_password = os.environ.get("POSTGRES_PASSWORD", "mysecretpassword")