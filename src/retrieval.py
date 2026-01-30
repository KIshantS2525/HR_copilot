# # backend/retrieval.py
# import numpy as np

# def retrieve(query, index, chunks, sources, embedder, k=4, score_threshold=0.25):
#     """Retrieve top-k most relevant chunks using vector similarity."""
#     # Embed query
#     q_emb = embedder.encode([query])
    
#     # Query ChromaDB collection
#     try:
#         results = index.query(
#             query_embeddings=q_emb.tolist(),
#             n_results=k,
#             include=["documents", "metadatas", "distances"]
#         )
#     except Exception as e:
#         print(f"Error querying ChromaDB: {e}")
#         # Try alternative query method without embeddings
#         try:
#             results = index.query(
#                 query_texts=[query],
#                 n_results=k,
#                 include=["documents", "metadatas", "distances"]
#             )
#         except Exception as e2:
#             print(f"Error with text query too: {e2}")
#             return []
    
#     # Process results
#     retrieved_results = []
    
#     if results and results.get("documents") and len(results["documents"][0]) > 0:
#         retrieved_chunks = results["documents"][0]
#         retrieved_sources = [m.get("source") for m in results["metadatas"][0]]
#         distances = results["distances"][0] if results.get("distances") else []
        
#         print(f"Found {len(retrieved_chunks)} documents from query")
#         print(f"Distances received: {distances}")
        
#         # Calculate similarity scores from distances
#         # ChromaDB typically returns Euclidean distances (L2) for embeddings
#         # We need to convert to cosine-like similarity (0-1 range)
#         scores = []
        
#         if distances:
#             # Method 1: For Euclidean distance, convert to similarity
#             # similarity = 1 / (1 + distance)  # This gives 0-1 range
#             for d in distances:
#                 # Normalize distance to 0-1 range first
#                 # Assuming typical embedding space, we can scale
#                 normalized_d = d / 10.0  # Adjust scaling factor based on your embedding space
#                 similarity = 1.0 / (1.0 + normalized_d)
#                 scores.append(min(max(similarity, 0.0), 1.0))  # Clamp to 0-1
            
#             # Method 2: Alternatively, convert to cosine similarity
#             # For L2 normalized embeddings, cosine similarity = 1 - (d^2)/2
#             # scores = [1.0 - (d*d)/2.0 for d in distances]
#         else:
#             # If no distances, assign decreasing scores
#             scores = [1.0 - (i * 0.1) for i in range(len(retrieved_chunks))]
        
#         print(f"Calculated scores: {scores}")
        
#         # Combine, sort by score (highest first)
#         combined = list(zip(retrieved_chunks, retrieved_sources, scores))
#         sorted_items = sorted(combined, key=lambda x: x[2], reverse=True)
        
#         # Filter by threshold and format
#         for text, source, score in sorted_items:
#             if score >= score_threshold:
#                 retrieved_results.append({
#                     "text": text,
#                     "source": source,
#                     "score": float(score)
#                 })
    
#     print(f"Retrieved {len(retrieved_results)} relevant documents (after threshold filtering).")
    
#     # If no results after threshold, return top result regardless of threshold
#     if not retrieved_results and len(retrieved_chunks) > 0:
#         print("No documents passed threshold, returning top result anyway.")
#         text, source, score = sorted_items[0]
#         retrieved_results.append({
#             "text": text,
#             "source": source,
#             "score": float(score)
#         })
    
#     return retrieved_results


# backend/retrieval.py
# import numpy as np

# NO_RESULT_RESPONSE = {
#     "text": "I am sorry, I am not able to help with this request. Please contact to hr@ascentt.com for further assistance.",
#     "source": "system",
#     "score": 0.0
# }

# def retrieve(query, index, chunks, sources, embedder, k=8, score_threshold=0.25):
#     """
#     Retrieve relevant chunks with adaptive filtering.
    
#     Key improvements:
#     1. Dynamic threshold based on result quality
#     2. Minimum relevance requirements
#     3. Return empty when matches are poor
#     """
    
#     try:
#         results = index.query(
#             query_texts=[query],
#             n_results=k,
#             include=["documents", "metadatas", "distances"]
#         )
#     except Exception as e:
#         print(f"Error querying ChromaDB: {e}")
#         return [NO_RESULT_RESPONSE]
    
#     if not results or not results.get("documents") or not results["documents"][0]:
#         return [NO_RESULT_RESPONSE]
    
#     documents = results["documents"][0]
#     metadatas = results.get("metadatas", [[]])[0]
#     distances = results.get("distances", [[]])[0]
    
#     if not distances:
#         return [NO_RESULT_RESPONSE]
    
#     print(f"Query: '{query}'")
#     print(f"Distances: {[f'{d:.3f}' for d in distances]}")
    
#     # Calculate baseline: what's a "good" distance for this query?
#     # Look at the distribution of distances
#     min_distance = min(distances)
#     avg_distance = sum(distances) / len(distances)
    
#     # Adaptive threshold: if even the best match is poor, return no results
#     if min_distance > 1.2:  # Very poor best match
#         print(f"Best match too poor (distance={min_distance:.3f}), returning no results")
#         return [NO_RESULT_RESPONSE]
    
#     if min_distance > 0.8:  # Poor best match
#         # Only accept very good matches within this poor set
#         adaptive_threshold = 0.4
#     else:
#         adaptive_threshold = score_threshold
    
#     # Process results
#     retrieved_results = []
#     for i, (doc, distance) in enumerate(zip(documents, distances)):
#         # Get source
#         source = "unknown"
#         if i < len(metadatas) and metadatas[i]:
#             source = metadatas[i].get("source", "unknown")
        
#         # Convert distance to similarity (better formula for cosine similarity)
#         # For normalized embeddings: similarity ≈ 1 - distance (for small distances)
#         if distance < 1.0:
#             score = 1.0 - distance
#         else:
#             score = 1.0 / (1.0 + distance)
        
#         # Apply adaptive threshold
#         if score >= adaptive_threshold:
#             # Additional quality check: document should have reasonable length
#             if len(doc.strip()) > 20:  # At least 20 characters
#                 retrieved_results.append({
#                     "text": doc,
#                     "source": source,
#                     "score": float(score)
#                 })
    
#     # Only return if we have at least one good match
#     if retrieved_results:
#         # Sort by score
#         retrieved_results.sort(key=lambda x: x["score"], reverse=True)
        
#         # Don't return poor matches mixed with good ones
#         if retrieved_results[0]["score"] > 0.6 and len(retrieved_results) > 1:
#             # If we have a good match, filter out very poor ones
#             retrieved_results = [r for r in retrieved_results if r["score"] > 0.3]
        
#         # FIXED: Correct f-string syntax
#         scores_str = ', '.join([f"{r['score']:.3f}" for r in retrieved_results])
#         print(f"Returning {len(retrieved_results)} documents (scores: {scores_str})")
#         return retrieved_results
    
#     print("No documents passed adaptive threshold")
#     return [NO_RESULT_RESPONSE]

# backend/retrieval.py
# backend/retrieval.py

NO_RESULT_RESPONSE = {
    "text": "I am sorry, I am not able to help with this request. Please contact to hr@ascentt.com for further assistance.",
    "source": "system",
    "score": 0.0
}

def retrieve(query, index, chunks, sources, embedder, k=4, score_threshold=0.25):
    """Retrieve top-k most relevant chunks using vector similarity."""
    try:
        # Query ChromaDB - it handles everything including sorting
        results = index.query(
            query_texts=[query],  # Let ChromaDB handle the embedding internally
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print(f"Error querying ChromaDB: {e}")
        return [NO_RESULT_RESPONSE]
    
    # Check if we got results
    if not results or not results.get("documents") or not results["documents"][0]:
        return [NO_RESULT_RESPONSE]
    
    # Process results (already sorted by ChromaDB)
    documents = results["documents"][0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    
    retrieved_results = []
    for i, doc in enumerate(documents):
        # Get source
        source = "unknown"
        if i < len(metadatas) and metadatas[i]:
            source = metadatas[i].get("source", "unknown")
        
        # Convert distance to similarity score
        score = 0.5
        if i < len(distances):
            distance = distances[i]
            score = 1.0 / (1.0 + distance)
        
        if score >= score_threshold:
            retrieved_results.append({
                "text": doc,
                "source": source,
                "score": float(score)
            })
    
    return retrieved_results if retrieved_results else [NO_RESULT_RESPONSE]