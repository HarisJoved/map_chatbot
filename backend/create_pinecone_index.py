import os
from pinecone import Pinecone, ServerlessSpec

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY","pcsk_2cdGij_QQPzzPGZtMqkueia6adYSrrv1cezM6r8o8pr7qeF5jbUYn51Dqq9fMP6UtNqQHA")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "locations-index")
PINECONE_DIM = int(os.getenv("PINECONE_DIM", 768))
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")  # or "gcp"
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

pc = Pinecone(api_key=PINECONE_API_KEY)

# List existing indexes
existing_indexes = pc.list_indexes().names()

if PINECONE_INDEX in existing_indexes:
    print(f"Index '{PINECONE_INDEX}' already exists.")
else:
    pc.create_index(
        name=PINECONE_INDEX,
        dimension=PINECONE_DIM,
        metric="cosine",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION
        )
    )
    print(f"Index '{PINECONE_INDEX}' created with dimension {PINECONE_DIM} on {PINECONE_CLOUD} in {PINECONE_REGION}.") 