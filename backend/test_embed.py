import os
import asyncio
from app.services.embedding_service import index_chunks

def test():
    try:
        from app.services.embedding_service import get_embedding
        vec = get_embedding("Hello world")
        print(f"Vector dim: {len(vec)}")
        index_chunks("test-file-id", [{"text": "Hello world", "chunk_index": 0}])
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
