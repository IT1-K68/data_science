from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

import time


DATA_PATH = "../data/tmdb_movies_final.csv"
DB_PATH = "../db/qdrant"
EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"

# Load csv file
loader = CSVLoader(file_path=DATA_PATH, encoding="utf-8-sig")
csv_data = loader.load()


# Create embedding model
model_name = EMBEDDING_MODEL_NAME
model_kwargs = {
    "device": "cpu"
}
encode_kwargs = {
    "normalize_embeddings": False
}
embedding_model = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# Save to Qdrant DB
client = QdrantClient(path=DB_PATH)
client.create_collection(
    collection_name="demo_collection2",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)
vector_store = QdrantVectorStore(
    client=client,
    collection_name="demo_collection2",
    embedding=embedding_model,
)

total = len(csv_data)
BATCH = 100

for i in range(0, total, BATCH):

    start = time.time()
    batch = csv_data[i:i+BATCH]
    vector_store.add_documents(batch)
    end = time.time()
    process_time = end - start

    progress = (i + len(batch)) / total * 100

    print(f"Progress: {progress:.2f}%  ({i + len(batch)}/{total}) in {process_time:.2f}ms")

client.close()