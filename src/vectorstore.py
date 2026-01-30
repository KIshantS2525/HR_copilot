import os
import hashlib
from sentence_transformers import SentenceTransformer
from pdf_loader import load_pdf
from chunking import chunk_text
from config import PDF_DIR, EMBED_MODEL

try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception as e:
    chromadb = None


def _file_id(fname: str) -> str:
    return os.path.basename(fname)


def build_vectorstore(persist_dir: str = None):
    """Build or load a persistent ChromaDB collection for PDF chunks.

    - Uses `SentenceTransformer` for embeddings via Chroma's embedding wrapper.
    - Skips embedding files already present in the collection (checks metadata `source`).
    - Returns (collection, all_chunks, sources, embedder)
    """
    if chromadb is None:
        raise ImportError(
            "chromadb is required for persistent vectorstore. Install with `pip install chromadb`"
        )

    # prepare PDF list
    pdf_files = [
        os.path.join(PDF_DIR, f)
        for f in os.listdir(PDF_DIR)
        if f.lower().endswith(".pdf")
    ]

    # ChromaDB persistence directory
    if persist_dir is None:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        persist_dir = os.path.join(base, "chroma_db")
    os.makedirs(persist_dir, exist_ok=True)

    # Updated ChromaDB client initialization for newer versions
    client = chromadb.PersistentClient(path=persist_dir)

    embedder = SentenceTransformer(EMBED_MODEL)
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )

    collection_name = "pdfs"
    # create or get collection
    try:
        collection = client.get_collection(name=collection_name, embedding_function=embedding_function)
    except Exception:
        collection = client.create_collection(
            name=collection_name, embedding_function=embedding_function
        )

    # For each PDF, skip if there are already documents with this source
    new_added = False
    for pdf in pdf_files:
        source = _file_id(pdf)
        try:
            # count supports `where` filtering in newer chroma versions
            existing_count = collection.count(where={"source": source})
        except Exception:
            # fallback: fetch metadatas and check manually
            try:
                res = collection.get(include=["metadatas"])
                existing_count = sum(1 for m in res.get("metadatas", []) if m.get("source") == source)
            except Exception:
                existing_count = 0

        if existing_count > 0:
            continue

        text = load_pdf(pdf)
        chunks = chunk_text(text)

        if not chunks:
            continue

        ids = []
        metadatas = []
        documents = []
        for i, c in enumerate(chunks):
            # deterministic id per file-chunk
            chunk_hash = hashlib.sha1((source + str(i) + c).encode("utf-8")).hexdigest()
            ids.append(f"{source}_{i}_{chunk_hash}")
            metadatas.append({"source": source, "chunk_index": i})
            documents.append(c)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        new_added = True

    # No need to manually persist with PersistentClient
    # For PersistentClient, data is automatically persisted

    # return all documents and sources from collection
    try:
        res = collection.get(include=["documents", "metadatas", "ids"])
        all_chunks = []
        sources = []
        for doc, md in zip(res.get("documents", []), res.get("metadatas", [])):
            all_chunks.append(doc)
            sources.append(md.get("source"))
    except Exception:
        all_chunks = []
        sources = []

    return collection, all_chunks, sources, embedder