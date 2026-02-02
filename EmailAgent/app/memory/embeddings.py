from dotenv import load_dotenv
from app.llm.gemini import client
from google.genai import types

load_dotenv()


def embed_text(text: str) -> list[float]:
    """
    Convert text into a 768-dim embedding vector using Gemini.
    Uses gemini-embedding-001 with output_dimensionality=768 to match database schema.
    """

    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(
            output_dimensionality=768,
            task_type="RETRIEVAL_DOCUMENT"  # Optimized for document search/RAG
        )
    )

    # ✅ Correct for your SDK version
    embedding = response.embeddings[0].values
    
    # Verify we got the expected dimension
    if len(embedding) != 768:
        raise ValueError(f"Expected 768-dim embedding, got {len(embedding)}")

    return embedding
