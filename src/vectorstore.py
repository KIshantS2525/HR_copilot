# import os
# import hashlib
# from sentence_transformers import SentenceTransformer
# from pdf_loader import load_pdf
# from chunking import chunk_text
# from config import PDF_DIR, EMBED_MODEL

# try:
#     import chromadb
#     from chromadb.utils import embedding_functions
# except Exception as e:
#     chromadb = None


# def _file_id(fname: str) -> str:
#     return os.path.basename(fname)


# def build_vectorstore(persist_dir: str = None):
#     """Build or load a persistent ChromaDB collection for PDF chunks.

#     - Uses `SentenceTransformer` for embeddings via Chroma's embedding wrapper.
#     - Skips embedding files already present in the collection (checks metadata `source`).
#     - Returns (collection, all_chunks, sources, embedder)
#     """
#     if chromadb is None:
#         raise ImportError(
#             "chromadb is required for persistent vectorstore. Install with `pip install chromadb`"
#         )

#     # prepare PDF list
#     pdf_files = [
#         os.path.join(PDF_DIR, f)
#         for f in os.listdir(PDF_DIR)
#         if f.lower().endswith(".pdf")
#     ]

#     # ChromaDB persistence directory
#     if persist_dir is None:
#         base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
#         persist_dir = os.path.join(base, "chroma_db")
#     os.makedirs(persist_dir, exist_ok=True)

#     # Updated ChromaDB client initialization for newer versions
#     client = chromadb.PersistentClient(path=persist_dir)

#     embedder = SentenceTransformer(EMBED_MODEL)
#     embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
#         model_name=EMBED_MODEL
#     )

#     collection_name = "pdfs"
#     # create or get collection
#     try:
#         collection = client.get_collection(name=collection_name, embedding_function=embedding_function)
#     except Exception:
#         collection = client.create_collection(
#             name=collection_name, embedding_function=embedding_function
#         )

#     # For each PDF, skip if there are already documents with this source
#     new_added = False
#     for pdf in pdf_files:
#         source = _file_id(pdf)
#         try:
#             # count supports `where` filtering in newer chroma versions
#             existing_count = collection.count(where={"source": source})
#         except Exception:
#             # fallback: fetch metadatas and check manually
#             try:
#                 res = collection.get(include=["metadatas"])
#                 existing_count = sum(1 for m in res.get("metadatas", []) if m.get("source") == source)
#             except Exception:
#                 existing_count = 0

#         if existing_count > 0:
#             continue

#         text = load_pdf(pdf)
#         chunks = chunk_text(text)

#         if not chunks:
#             continue

#         ids = []
#         metadatas = []
#         documents = []
#         for i, c in enumerate(chunks):
#             # deterministic id per file-chunk
#             chunk_hash = hashlib.sha1((source + str(i) + c).encode("utf-8")).hexdigest()
#             ids.append(f"{source}_{i}_{chunk_hash}")
#             metadatas.append({"source": source, "chunk_index": i})
#             documents.append(c)

#         collection.add(ids=ids, documents=documents, metadatas=metadatas)
#         new_added = True

#     # No need to manually persist with PersistentClient
#     # For PersistentClient, data is automatically persisted

#     # return all documents and sources from collection
#     try:
#         res = collection.get(include=["documents", "metadatas", "ids"])
#         all_chunks = []
#         sources = []
#         for doc, md in zip(res.get("documents", []), res.get("metadatas", [])):
#             all_chunks.append(doc)
#             sources.append(md.get("source"))
#     except Exception:
#         all_chunks = []
#         sources = []

#     return collection, all_chunks, sources, embedder

import os
import hashlib
import re
from typing import List, Tuple
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


def semantic_chunking(text: str, max_tokens: int = 400, overlap_tokens: int = 80) -> List[str]:
    """
    Split text semantically based on headings and sentences.
    Uses overlapping windows to avoid cutting facts in the middle.
    """
    if not text or not text.strip():
        return []
    
    # Clean text
    text = text.strip()
    
    # First try semantic splitting by headings
    heading_pattern = r'\n(?:#{1,3}\s+|\d+\.\s+\w+|[A-Z][A-Z\s]{3,}:?)\n'
    sections = re.split(heading_pattern, text)
    
    if len(sections) > 1:
        chunks = []
        current_chunk = ""
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Estimate tokens (4 chars ≈ 1 token)
            if len(current_chunk) / 4 + len(section) / 4 <= max_tokens:
                current_chunk += section + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        if chunks:
            return chunks
    
    # Fallback: split by paragraphs with overlap
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not paragraphs:
        # Last resort: split by sentences
        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        paragraphs = sentences
    
    chunks = []
    current_chunk = ""
    
    for i, para in enumerate(paragraphs):
        if not para:
            continue
            
        para_tokens = len(para) / 4  # Rough estimate
        
        if len(current_chunk) / 4 + para_tokens <= max_tokens:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Apply overlap: include last part of previous chunk
            if chunks and overlap_tokens > 0:
                prev_chunk = chunks[-1]
                prev_words = prev_chunk.split()
                overlap_words = prev_words[-overlap_tokens:] if len(prev_words) > overlap_tokens else prev_words
                current_chunk = ' '.join(overlap_words) + "\n\n" + para + "\n\n"
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Ensure chunks aren't too small
    chunks = [c for c in chunks if len(c.split()) >= 10]  # At least 10 words
    
    return chunks


def build_vectorstore(persist_dir: str = None):
    """Build or load a persistent ChromaDB collection with semantic chunking."""
    if chromadb is None:
        raise ImportError(
            "chromadb is required for persistent vectorstore. Install with `pip install chromadb`"
        )

    pdf_files = [
        os.path.join(PDF_DIR, f)
        for f in os.listdir(PDF_DIR)
        if f.lower().endswith(".pdf")
    ]
    
    if not pdf_files:
        print(f"No PDF files found in {PDF_DIR}")
        # Create empty collection
        return _create_empty_collection(persist_dir)

    if persist_dir is None:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        persist_dir = os.path.join(base, "chroma_db")
    os.makedirs(persist_dir, exist_ok=True)

    client = chromadb.PersistentClient(path=persist_dir)
    embedder = SentenceTransformer(EMBED_MODEL)
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )

    collection_name = "pdfs"
    try:
        collection = client.get_collection(name=collection_name, embedding_function=embedding_function)
        print(f"Loaded existing collection '{collection_name}'")
    except Exception:
        collection = client.create_collection(
            name=collection_name, embedding_function=embedding_function
        )
        print(f"Created new collection '{collection_name}'")

    new_added = False
    total_chunks = 0
    
    for pdf in pdf_files:
        source = _file_id(pdf)
        
        # Check if file already exists in collection
        try:
            existing_count = collection.count(where={"source": source})
            if existing_count > 0:
                print(f"✓ {source} already in collection ({existing_count} chunks)")
                total_chunks += existing_count
                continue
        except Exception as e:
            print(f"Warning checking existing chunks for {source}: {e}")
            # Continue anyway

        print(f"Processing {source}...")
        try:
            text = load_pdf(pdf)
            if not text or not text.strip():
                print(f"  Warning: Empty text extracted from {source}")
                continue
                
            print(f"  Extracted {len(text)} characters")
            
            # Use semantic chunking
            chunks = semantic_chunking(text, max_tokens=400, overlap_tokens=80)
            
            # Fallback to original chunking if semantic chunking fails
            if not chunks or len(chunks) == 0:
                print(f"  Semantic chunking failed, using fallback chunking")
                chunks = chunk_text(text) if hasattr(chunk_text, '__call__') else []
            
            if not chunks:
                print(f"  No chunks generated from {source}")
                continue
            
            print(f"  Generated {len(chunks)} chunks")
            
            ids = []
            metadatas = []
            documents = []
            
            for i, c in enumerate(chunks):
                c = c.strip()
                if len(c) < 30:  # Skip very short chunks
                    continue
                    
                chunk_hash = hashlib.sha1((source + str(i) + c).encode("utf-8")).hexdigest()
                ids.append(f"{source}_{i}_{chunk_hash}")
                
                metadatas.append({
                    "source": source,
                    "chunk_index": i,
                    "chunk_length": len(c),
                    "has_numbers": bool(re.search(r'\d+', c)),
                    "has_dates": bool(re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', c))
                })
                documents.append(c)
            
            if documents:
                collection.add(ids=ids, documents=documents, metadatas=metadatas)
                total_chunks += len(documents)
                new_added = True
                print(f"  ✓ Added {len(documents)} chunks to collection")
            else:
                print(f"  No valid documents to add")
                
        except Exception as e:
            print(f"  Error processing {source}: {e}")
            continue
    
    # Get all documents and sources from collection
    try:
        res = collection.get(include=["documents", "metadatas"])
        all_chunks = res.get("documents", [])
        sources = []
        for md in res.get("metadatas", []):
            sources.append(md.get("source", "unknown") if md else "unknown")
        
        print(f"\nVector store ready with {len(all_chunks)} total chunks")
        
        # Debug: Show sample chunks
        if all_chunks:
            print(f"Sample chunk (first 200 chars): {all_chunks[0][:200]}...")
        
    except Exception as e:
        print(f"Error getting collection contents: {e}")
        all_chunks = []
        sources = []
    
    return collection, all_chunks, sources, embedder


def _create_empty_collection(persist_dir: str):
    """Create an empty collection when no PDFs are found."""
    import chromadb
    from chromadb.utils import embedding_functions
    from sentence_transformers import SentenceTransformer
    
    if persist_dir is None:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        persist_dir = os.path.join(base, "chroma_db")
    os.makedirs(persist_dir, exist_ok=True)
    
    client = chromadb.PersistentClient(path=persist_dir)
    embedder = SentenceTransformer(EMBED_MODEL)
    embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    
    collection_name = "pdfs"
    try:
        collection = client.get_collection(name=collection_name, embedding_function=embedding_function)
    except Exception:
        collection = client.create_collection(
            name=collection_name, embedding_function=embedding_function
        )
    
    print("Created empty collection (no PDFs found)")
    return collection, [], [], embedder