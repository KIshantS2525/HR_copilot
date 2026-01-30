import os
import hashlib
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from vectorstore import build_vectorstore
from pdf_loader import load_pdf
from chunking import chunk_text
from config import PDF_DIR

app = FastAPI(title="HR Copilot API", description="API for uploading and managing document embeddings")

# Store vectorstore instance (lazy loaded)
_vectorstore_data = None


def get_or_build_vectorstore():
    """Lazy load vectorstore on first use."""
    global _vectorstore_data
    if _vectorstore_data is None:
        _vectorstore_data = build_vectorstore()
    return _vectorstore_data


def _get_stored_files() -> set:
    """Get set of all files currently in the collection."""
    try:
        collection, all_chunks, sources, embedder = get_or_build_vectorstore()
        if sources:
            return set(sources)
        
        # If sources is empty, try to get from collection directly
        try:
            res = collection.get(include=["metadatas"])
            sources_set = set(m.get("source") for m in res.get("metadatas", []) if m.get("source"))
            return sources_set
        except Exception:
            return set()
    except Exception:
        return set()


def _save_uploaded_file(upload_file: UploadFile, target_dir: str) -> str:
    """Save uploaded file to target directory and return file path."""
    os.makedirs(target_dir, exist_ok=True)
    file_path = os.path.join(target_dir, upload_file.filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        content = upload_file.file.read()
        f.write(content)
    
    return file_path


def _add_document_to_vectorstore(file_path: str):
    """Load document, chunk it, and add to vectorstore."""
    source = os.path.basename(file_path)
    
    try:
        text = load_pdf(file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load document: {str(e)}")
    
    chunks = chunk_text(text)
    
    if not chunks:
        raise HTTPException(status_code=400, detail="Document contains no extractable text.")
    
    # Get fresh vectorstore instance (don't use cached one)
    collection, _, _, embedder = build_vectorstore()
    
    # Check if file already exists in the collection
    try:
        existing_count = collection.count(where={"source": source})
        if existing_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"File '{source}' already exists in vectorstore. Delete it first if you want to re-upload."
            )
    except Exception:
        # Fallback method for older ChromaDB versions
        try:
            res = collection.get(include=["metadatas"])
            existing_count = sum(1 for m in res.get("metadatas", []) if m.get("source") == source)
            if existing_count > 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File '{source}' already exists in vectorstore. Delete it first if you want to re-upload."
                )
        except Exception:
            pass
    
    # Prepare documents for insertion
    ids = []
    metadatas = []
    documents = []
    
    for i, c in enumerate(chunks):
        # deterministic id per file-chunk
        chunk_hash = hashlib.sha1((source + str(i) + c).encode("utf-8")).hexdigest()
        ids.append(f"{source}_{i}_{chunk_hash}")
        metadatas.append({"source": source, "chunk_index": i})
        documents.append(c)
    
    try:
        # Add to collection
        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"Added {len(ids)} chunks from {source} to vectorstore")
        
        # Force refresh the global cache
        global _vectorstore_data
        _vectorstore_data = None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add document to vectorstore: {str(e)}")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a PDF file for embedding.
    
    - Automatically processes the file and creates embeddings
    - Skips processing if the file is already embedded
    """
    # Validate file extension
    filename = file.filename
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file format. Only .pdf files are supported."
        )
    
    # Save uploaded file
    try:
        file_path = _save_uploaded_file(file, PDF_DIR)
        print(f"Saved file to: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Add to vectorstore
    try:
        _add_document_to_vectorstore(file_path)
    except HTTPException:
        # If upload fails, delete the saved file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    
    # Force refresh the stored files list
    global _vectorstore_data
    _vectorstore_data = None
    
    return JSONResponse(
        status_code=201,
        content={
            "message": f"File '{filename}' uploaded and embedded successfully.",
            "filename": filename,
            "status": "embedded"
        }
    )



@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    Delete embeddings for a specific file.
    
    - Removes all chunks associated with the file from the vectorstore
    - Also deletes the file from disk
    """
    # Get fresh vectorstore instance
    collection, _, _, _ = build_vectorstore()
    
    # Try to find documents with this source
    try:
        # Method 1: Use where filter (newer ChromaDB) - Get everything and extract IDs
        res = collection.get(
            where={"source": filename},
            include=["metadatas"]  # Don't include "ids" - we'll get all data and IDs come automatically
        )
        matching_ids = res.get("ids", [])
    except Exception as e:
        print(f"Error with where filter: {e}")
        try:
            # Method 2: Get all and filter (works with older ChromaDB)
            res = collection.get(include=["metadatas"])  # Just get metadatas
            # IDs are always returned even if not in include
            matching_ids = []
            for id_, md in zip(res.get("ids", []), res.get("metadatas", [])):
                if md.get("source") == filename:
                    matching_ids.append(id_)
        except Exception as e2:
            print(f"Error with manual filtering: {e2}")
            raise HTTPException(status_code=500, detail=f"Failed to query vectorstore: {str(e2)}")
    
    if not matching_ids:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in vectorstore.")
    
    # Delete from vectorstore
    try:
        collection.delete(ids=matching_ids)
        print(f"Deleted {len(matching_ids)} chunks for file '{filename}' from vectorstore")
        
        # Force refresh the global cache
        global _vectorstore_data
        _vectorstore_data = None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete from vectorstore: {str(e)}")
    
    # Delete file from disk if it exists
    file_path = os.path.join(PDF_DIR, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Deleted file from disk: {file_path}")
        except Exception as e:
            # Log but don't fail the request if disk deletion fails
            print(f"Warning: Failed to delete file from disk: {str(e)}")
    
    return JSONResponse(
        status_code=200,
        content={
            "message": f"File '{filename}' and its embeddings deleted successfully.",
            "deleted_chunks": len(matching_ids)
        }
    )
@app.get("/files")
async def list_files():
    """
    List all files currently embedded in the vectorstore.
    """
    # Force refresh to get latest data
    global _vectorstore_data
    _vectorstore_data = None
    
    collection, all_chunks, sources, embedder = get_or_build_vectorstore()
    
    # Try multiple methods to get files
    files_set = set()
    
    # Method 1: Use sources from build_vectorstore
    if sources:
        files_set.update(sources)
    
    # Method 2: Query collection directly
    try:
        res = collection.get(include=["metadatas"])
        for m in res.get("metadatas", []):
            source = m.get("source")
            if source:
                files_set.add(source)
    except Exception as e:
        print(f"Warning: Could not query collection for metadata: {e}")
    
    # Method 3: Count per source
    for file_name in os.listdir(PDF_DIR):
        if file_name.lower().endswith('.pdf'):
            try:
                count = collection.count(where={"source": file_name})
                if count > 0:
                    files_set.add(file_name)
            except Exception:
                pass
    
    files_list = sorted(list(files_set))
    
    return JSONResponse(
        status_code=200,
        content={
            "count": len(files_list),
            "files": files_list,
            "total_chunks": collection.count() if hasattr(collection, 'count') else 0
        }
    )


@app.get("/stats")
async def get_stats():
    """Get statistics about the vectorstore."""
    try:
        collection, all_chunks, sources, embedder = get_or_build_vectorstore()
        
        # Get total count
        total_chunks = collection.count()
        
        # Get per-file counts
        file_stats = {}
        files_set = _get_stored_files()
        
        for filename in files_set:
            try:
                count = collection.count(where={"source": filename})
                file_stats[filename] = count
            except Exception:
                file_stats[filename] = "unknown"
        
        return JSONResponse(
            status_code=200,
            content={
                "total_chunks": total_chunks,
                "total_files": len(files_set),
                "file_stats": file_stats
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        collection, all_chunks, sources, embedder = get_or_build_vectorstore()
        count = collection.count()
        return JSONResponse(
            status_code=200, 
            content={
                "status": "healthy",
                "collection_count": count,
                "embedding_model": embedder.__class__.__name__
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=503, 
            content={
                "status": "unhealthy", 
                "error": str(e)
            }
        )


@app.post("/refresh")
async def refresh_vectorstore():
    """Force refresh the vectorstore cache and rebuild."""
    global _vectorstore_data
    _vectorstore_data = None
    
    # Rebuild vectorstore
    collection, all_chunks, sources, embedder = get_or_build_vectorstore()
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Vectorstore refreshed successfully.",
            "total_chunks": collection.count(),
            "total_files": len(set(sources)) if sources else 0
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)