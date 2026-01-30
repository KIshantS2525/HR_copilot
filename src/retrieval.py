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

# NO_RESULT_RESPONSE = {
#     "text": "I am sorry, I am not able to help with this request. Please contact to hr@ascentt.com for further assistance.",
#     "source": "system",
#     "score": 0.0
# }

# def retrieve(query, index, chunks, sources, embedder, k=4, score_threshold=0.25):
#     """Retrieve top-k most relevant chunks using vector similarity."""
#     try:
#         # Query ChromaDB - it handles everything including sorting
#         results = index.query(
#             query_texts=[query],  # Let ChromaDB handle the embedding internally
#             n_results=k,
#             include=["documents", "metadatas", "distances"]
#         )
#     except Exception as e:
#         print(f"Error querying ChromaDB: {e}")
#         return [NO_RESULT_RESPONSE]
    
#     # Check if we got results
#     if not results or not results.get("documents") or not results["documents"][0]:
#         return [NO_RESULT_RESPONSE]
    
#     # Process results (already sorted by ChromaDB)
#     documents = results["documents"][0]
#     metadatas = results.get("metadatas", [[]])[0]
#     distances = results.get("distances", [[]])[0]
    
#     retrieved_results = []
#     for i, doc in enumerate(documents):
#         # Get source
#         source = "unknown"
#         if i < len(metadatas) and metadatas[i]:
#             source = metadatas[i].get("source", "unknown")
        
#         # Convert distance to similarity score
#         score = 0.5
#         if i < len(distances):
#             distance = distances[i]
#             score = 1.0 / (1.0 + distance)
        
#         if score >= score_threshold:
#             retrieved_results.append({
#                 "text": doc,
#                 "source": source,
#                 "score": float(score)
#             })
    
#     return retrieved_results if retrieved_results else [NO_RESULT_RESPONSE]

# backend/retrieval.py
from typing import List, Dict, Any, Optional
import numpy as np

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("Warning: rank-bm25 not installed. Using dense search only.")

NO_RESULT_RESPONSE = {
    "text": "I am sorry, I am not able to help with this request. Please contact hr@ascentt.com for further assistance.",
    "source": "system",
    "score": 0.0
}

class HybridRetriever:
    """Hybrid retriever combining dense vector search and BM25 keyword search."""
    
    def __init__(self, index, chunks: List[str], sources: List[str], embedder):
        self.index = index  # ChromaDB/FAISS index for dense vectors
        self.chunks = chunks
        self.sources = sources
        self.embedder = embedder
        
        # Initialize BM25 only if we have chunks and package is available
        self.bm25 = None
        if BM25_AVAILABLE and chunks and len(chunks) > 0:
            self.tokenized_chunks = [self._tokenize(chunk) for chunk in chunks]
            # Filter out empty tokenized chunks
            self.tokenized_chunks = [tc for tc in self.tokenized_chunks if tc]
            if self.tokenized_chunks:
                self.bm25 = BM25Okapi(self.tokenized_chunks)
                print(f"BM25 initialized with {len(self.tokenized_chunks)} chunks")
            else:
                print("Warning: No valid chunks for BM25 initialization")
        else:
            if not BM25_AVAILABLE:
                print("BM25 not available, using dense search only")
            else:
                print(f"Warning: Empty chunks list ({len(chunks)} chunks)")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer for BM25."""
        if not text or not text.strip():
            return []
        return text.lower().split()
    
    def _bm25_search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Perform BM25 keyword search."""
        if not self.bm25 or not query or not query.strip():
            return []
        
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []
        
        try:
            scores = self.bm25.get_scores(tokenized_query)
            # Get top-k BM25 results
            bm25_indices = np.argsort(scores)[::-1][:k]
            
            results = []
            for idx in bm25_indices:
                if scores[idx] > 0 and idx < len(self.chunks):  # Only include relevant results
                    results.append({
                        "text": self.chunks[idx],
                        "source": self.sources[idx] if idx < len(self.sources) else "unknown",
                        "score": float(scores[idx]),
                        "type": "bm25"
                    })
            return results
        except Exception as e:
            print(f"Error in BM25 search: {e}")
            return []
    
    def _dense_search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Perform dense vector search using ChromaDB."""
        if not query or not query.strip():
            return []
            
        try:
            results = self.index.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"Error querying ChromaDB: {e}")
            return []
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return []
        
        documents = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        dense_results = []
        for i, doc in enumerate(documents):
            source = "unknown"
            if i < len(metadatas) and metadatas[i]:
                source = metadatas[i].get("source", "unknown")
            
            # Convert distance to similarity score
            score = 0.5
            if i < len(distances):
                distance = distances[i]
                if distance is not None:
                    score = 1.0 / (1.0 + distance)
            
            dense_results.append({
                "text": doc,
                "source": source,
                "score": float(score),
                "type": "dense"
            })
        
        return dense_results
    
    def retrieve(self, query: str, k: int = 8, score_threshold: float = 0.25, 
                 alpha: float = 0.7) -> List[Dict[str, Any]]:
        """
        Perform hybrid search with reciprocal rank fusion.
        
        Args:
            query: Search query
            k: Number of results to return
            score_threshold: Minimum score threshold
            alpha: Weight for dense vs sparse (0.5 = equal, >0.5 = dense favored)
        """
        if not query or not query.strip():
            return [NO_RESULT_RESPONSE]
        
        # Get results from both methods
        dense_results = self._dense_search(query, k * 2)
        bm25_results = self._bm25_search(query, k * 2) if self.bm25 else []
        
        if not dense_results and not bm25_results:
            # Fallback: try pure dense search if hybrid fails
            print("Hybrid search failed, trying pure dense search...")
            return self._fallback_search(query, k, score_threshold)
        
        # If only one method has results, use it directly
        if not dense_results:
            print("Only BM25 results available")
            final_results = bm25_results
        elif not bm25_results:
            print("Only dense results available")
            final_results = dense_results
        else:
            # Combine results using Reciprocal Rank Fusion (RRF)
            print(f"Combining {len(dense_results)} dense + {len(bm25_results)} BM25 results")
            final_results = self._combine_results_rrf(dense_results, bm25_results, k)
        
        # Filter by threshold and return
        filtered_results = []
        for result in final_results[:k]:
            if result["score"] >= score_threshold:
                filtered_results.append({
                    "text": result["text"],
                    "source": result["source"],
                    "score": float(result["score"])
                })
        
        if filtered_results:
            print(f"Hybrid search returned {len(filtered_results)} results")
            return filtered_results
        
        return [NO_RESULT_RESPONSE]
    
    def _combine_results_rrf(self, dense_results: List[Dict], bm25_results: List[Dict], 
                            k: int) -> List[Dict]:
        """Combine dense and BM25 results using Reciprocal Rank Fusion."""
        combined_results = {}
        
        # Process dense results
        for rank, result in enumerate(dense_results, 1):
            key = (result["text"], result["source"])
            if key not in combined_results:
                combined_results[key] = result.copy()
                combined_results[key]["combined_score"] = 0
                combined_results[key]["ranks"] = []
            combined_results[key]["ranks"].append(rank)
        
        # Process BM25 results
        for rank, result in enumerate(bm25_results, 1):
            key = (result["text"], result["source"])
            if key not in combined_results:
                combined_results[key] = result.copy()
                combined_results[key]["combined_score"] = 0
                combined_results[key]["ranks"] = []
            combined_results[key]["ranks"].append(rank)
        
        # Calculate RRF scores (k=60 as per standard RRF)
        for result in combined_results.values():
            rrf_score = 0
            for rank in result["ranks"]:
                rrf_score += 1.0 / (rank + 60)
            result["combined_score"] = rrf_score
            result["score"] = rrf_score  # Update main score for sorting
        
        # Sort by combined score
        return sorted(combined_results.values(), 
                     key=lambda x: x["combined_score"], 
                     reverse=True)[:k]
    
    def _fallback_search(self, query: str, k: int, score_threshold: float) -> List[Dict[str, Any]]:
        """Fallback to simple dense search when hybrid fails."""
        try:
            results = self.index.query(
                query_texts=[query],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            print(f"Fallback search error: {e}")
            return [NO_RESULT_RESPONSE]
        
        if not results or not results.get("documents") or not results["documents"][0]:
            return [NO_RESULT_RESPONSE]
        
        documents = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        
        retrieved_results = []
        for i, doc in enumerate(documents):
            source = "unknown"
            if i < len(metadatas) and metadatas[i]:
                source = metadatas[i].get("source", "unknown")
            
            score = 0.5
            if i < len(distances):
                distance = distances[i]
                if distance is not None:
                    score = 1.0 / (1.0 + distance)
            
            if score >= score_threshold:
                retrieved_results.append({
                    "text": doc,
                    "source": source,
                    "score": float(score)
                })
        
        return retrieved_results if retrieved_results else [NO_RESULT_RESPONSE]


def retrieve(query, index, chunks, sources, embedder, k=4, score_threshold=0.25):
    """Legacy function wrapper for backward compatibility."""
    # Ensure chunks and sources are valid
    if not chunks or len(chunks) == 0:
        print("Warning: Empty chunks list passed to retrieve")
        # Try to get chunks from index
        try:
            if hasattr(index, 'get'):
                res = index.get(include=["documents", "metadatas"])
                chunks = res.get("documents", [])
                sources = [m.get("source", "unknown") for m in res.get("metadatas", [])]
                print(f"Retrieved {len(chunks)} chunks from index")
        except:
            pass
    
    retriever = HybridRetriever(index, chunks or [], sources or [], embedder)
    return retriever.retrieve(query, k=k, score_threshold=score_threshold)