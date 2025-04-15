# Add this at the beginning of your script to diagnose CUDA issues
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"Device: {torch.cuda.get_device_name(0)}")
else:
    print("CUDA not available. Check your installation.")

import json
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from scipy.sparse.linalg import svds
import time

# Get the directory of the current script (backend folder)
current_directory = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the JSON file (init.json) in the backend folder
json_path = os.path.join(current_directory, "init.json")

# Create a models directory if it doesn't exist
models_dir = os.path.join(current_directory, "models")
os.makedirs(models_dir, exist_ok=True)

# TF-IDF SVD Search class (similar to the one in app.py but optimized for preprocessing)
class TFIDFSVDSearch:
    def __init__(self, n_components= 30):
        self.n_components = n_components
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            min_df=2,       # Include all terms, even rare ones
            max_df=0.5,     # Filter out very common terms
            ngram_range=(1, 2)  # Include both unigrams and bigrams
        )
        self.documents = []  # Will contain raw document texts
        self.doc_lookup = {}  # Maps document index to (source, streamer, idx)
        self.u = None        # Document-concept matrix
        self.s = None        # Singular values 
        self.vt = None       # Concept-term matrix
        self.docs_compressed = None  # Normalized document vectors in concept space
        self.dimension_labels = []   # Labels for each SVD dimension
        
    def preprocess_documents(self, reddit_data, twitter_data, wiki_data, details_data):
        """Extract all documents from the various data sources and prepare for TF-IDF"""
        doc_idx = 0
        
        print("Processing Reddit data...")
        # Process Reddit posts
        for streamer, posts in reddit_data.items():
            for idx, post in enumerate(posts):
                self.documents.append(post["Title"])
                self.doc_lookup[doc_idx] = ("reddit", streamer, idx, post)
                doc_idx += 1
        
        print("Processing Twitter data...")
        # Process Twitter posts
        for streamer, tweets in twitter_data.items():
            for idx, tweet in enumerate(tweets):
                self.documents.append(tweet)
                self.doc_lookup[doc_idx] = ("twitter", streamer, idx, tweet)
                doc_idx += 1
        
        print("Processing Wiki data...")
        # Process Wiki data
        if isinstance(wiki_data, dict):
            for streamer, entry in wiki_data.items():
                if isinstance(entry, dict) and "wikipedia_summary" in entry:
                    self.documents.append(entry["wikipedia_summary"])
                    self.doc_lookup[doc_idx] = ("wiki", streamer, 0, entry)
                    doc_idx += 1
        elif isinstance(wiki_data, list):
            for idx, entry in enumerate(wiki_data):
                if isinstance(entry, dict) and "wikipedia_summary" in entry and "streamer" in entry:
                    self.documents.append(entry["wikipedia_summary"])
                    self.doc_lookup[doc_idx] = ("wiki", entry["streamer"], idx, entry)
                    doc_idx += 1
        
        print("Processing Details data...")
        # Process Details descriptions
        for streamer, details in details_data.items():
            description = str(details.get("Description", ""))
            if description.strip():
                self.documents.append(description)
                self.doc_lookup[doc_idx] = ("details", streamer, 0, details)
                doc_idx += 1
                
        print(f"Preprocessed {len(self.documents)} documents for TF-IDF and SVD")
    
    def fit(self):
        """Fit the TF-IDF model and perform SVD with GPU acceleration if available"""
        print("Fitting TF-IDF vectorizer...")
        start_time = time.time()
        td_matrix = self.vectorizer.fit_transform(self.documents)
        print(f"TF-IDF vectorization completed in {time.time() - start_time:.2f} seconds")
        
        print(f"TF-IDF matrix shape: {td_matrix.shape}")
        print(f"Vocabulary size: {len(self.vectorizer.vocabulary_)}")
        
        print(f"Performing SVD with {self.n_components} components...")
        start_time = time.time()
        
        try:
            import torch
            import cupy as cp
            if torch.cuda.is_available():
                print("Using GPU acceleration with CuPy")
                # Convert scipy sparse matrix to cupy sparse matrix
                import cupyx.scipy.sparse as cp_sparse
                from cupyx.scipy.sparse.linalg import svds as cp_svds
                
                # Convert to CSR format if not already
                if not isinstance(td_matrix, cp_sparse.csr_matrix):
                    if hasattr(td_matrix, "tocsr"):
                        td_matrix = td_matrix.tocsr()
                
                # Move data to GPU
                data_gpu = cp.array(td_matrix.data)
                indices_gpu = cp.array(td_matrix.indices)
                indptr_gpu = cp.array(td_matrix.indptr)
                
                # Create sparse matrix on GPU
                td_matrix_gpu = cp_sparse.csr_matrix(
                    (data_gpu, indices_gpu, indptr_gpu),
                    shape=td_matrix.shape
                )
                
                # Perform SVD on GPU
                u_gpu, s_gpu, vt_gpu = cp_svds(td_matrix_gpu, k=self.n_components)
                
                # Move results back to CPU
                self.u = cp.asnumpy(u_gpu)
                self.s = cp.asnumpy(s_gpu)
                self.vt = cp.asnumpy(vt_gpu)
                
                print(f"GPU-accelerated SVD completed in {time.time() - start_time:.2f} seconds")
            else:
                raise ImportError("CUDA is not available")
        except ImportError as e:
            print(f"GPU acceleration not available: {e}")
            print("Falling back to CPU implementation")
            
            # Use scipy's sparse SVD
            from scipy.sparse.linalg import svds
            self.u, self.s, self.vt = svds(td_matrix, k=self.n_components)
            print(f"CPU SVD completed in {time.time() - start_time:.2f} seconds")
        
        # Sort the SVD components by singular values
        idx = np.argsort(-self.s)
        self.s = self.s[idx]
        self.u = self.u[:, idx]
        self.vt = self.vt[idx, :]
        
        # Normalize document vectors for cosine similarity
        self.docs_compressed = normalize(self.u)
        
        # Store the vocabulary mapping
        self.index_to_word = {i: t for t, i in self.vectorizer.vocabulary_.items()}
        self.word_to_index = self.vectorizer.vocabulary_
        
        # Generate labels for each SVD dimension
        self.dimension_labels = self._generate_dimension_labels()
        
        print("Model training completed successfully")
        return self
    
    def _generate_dimension_labels(self, top_n=3):
        """Generate representative labels for each SVD dimension based on top words"""
        print("Generating dimension labels...")
        dimension_labels = []
        
        for i in range(self.n_components):
            dimension = self.vt[i, :]
            top_indices = np.argsort(-dimension)[:top_n]
            
            # Filter out any non-word tokens
            top_terms = []
            for idx in top_indices:
                term = self.index_to_word[idx]
                # Only include unigrams and filter out bigrams for labeling
                if " " not in term and len(term) > 2:
                    top_terms.append(term)
            
            # Create a concise label
            if top_terms:
                label = " + ".join(top_terms[:2])  # Use top 2 terms for brevity
            else:
                label = f"Dimension {i+1}"
                
            dimension_labels.append(label)
            
        return dimension_labels
    
    def save_model(self, directory):
        """Save all model components to disk"""
        # Save the vectorizer
        with open(os.path.join(directory, "vectorizer.pkl"), "wb") as f:
            pickle.dump(self.vectorizer, f)
        
        # Save SVD components
        np.save(os.path.join(directory, "u_matrix.npy"), self.u)
        np.save(os.path.join(directory, "s_values.npy"), self.s)
        np.save(os.path.join(directory, "vt_matrix.npy"), self.vt)
        
        # Save normalized document vectors
        np.save(os.path.join(directory, "docs_compressed.npy"), self.docs_compressed)
        
        # Save document lookup mappings
        with open(os.path.join(directory, "doc_lookup.pkl"), "wb") as f:
            pickle.dump(self.doc_lookup, f)
        
        # Save word mappings
        with open(os.path.join(directory, "index_to_word.pkl"), "wb") as f:
            pickle.dump(self.index_to_word, f)
        
        # Save dimension labels
        with open(os.path.join(directory, "dimension_labels.pkl"), "wb") as f:
            pickle.dump(self.dimension_labels, f)
        
        print(f"All model components saved to {directory}")


def main():
    print("Loading data from init.json...")
    # Load the JSON data with UTF-8 encoding
    with open(json_path, "r", encoding="utf-8") as file:
        combined_data = json.load(file)

    # Extract the individual datasets
    reddit_data = combined_data["reddit"]
    twitter_data = combined_data["twitter"]
    wiki_data = combined_data["wiki"]
    details_data = combined_data["details"]
    
    # Print data info
    print(f"Reddit data: {len(reddit_data)} streamers")
    print(f"Twitter data: {len(twitter_data)} streamers")
    if isinstance(wiki_data, dict):
        print(f"Wiki data: dict with {len(wiki_data)} entries")
    elif isinstance(wiki_data, list):
        print(f"Wiki data: list with {len(wiki_data)} entries")
    print(f"Details data: {len(details_data)} streamers")
    
    # Initialize and train the model
    print("\nInitializing TF-IDF SVD model...")
    search_engine = TFIDFSVDSearch(n_components=30)
    
    # Preprocess documents
    search_engine.preprocess_documents(reddit_data, twitter_data, wiki_data, details_data)
    
    # Fit the model
    print("\nTraining the model...")
    start_time = time.time()
    search_engine.fit()
    print(f"Total training time: {time.time() - start_time:.2f} seconds")
    
    # Save the model
    print("\nSaving model to disk...")
    search_engine.save_model(models_dir)
    
    print("\nPreprocessing completed successfully.")
    print(f"Model saved to {models_dir}")
    print("You can now run the app.py server with optimized loading.")


if __name__ == "__main__":
    main()