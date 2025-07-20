## Step 13: Address Embedding Model Loading Issue

### Problem Analysis

The `orka_debug_console_*.log` showed a warning: `Model files not found locally for sentence-transformers/all-MiniLM-L6-v2. May need to download.` This indicated that the embedding model, crucial for vector search in Redis, was not being loaded correctly, leading to `Vector search returned 0 results` and consequently empty `merged` dictionaries from `JoinNode`s.

### Proposed Solution

Explicitly set the `SENTENCE_TRANSFORMERS_HOME` environment variable to a known, accessible location within the project structure. This ensures that the `sentence-transformers` library downloads and caches its models in a predictable place, resolving potential issues with model discovery and loading.

### Detailed Actions

1.  **Modified `orka/utils/embedder.py`**:
    *   Added `import os`.
    *   Set `os.environ['SENTENCE_TRANSFORMERS_HOME']` to `os.path.join(os.path.dirname(os.path.abspath(__file__)), '..\', '..\', 'models', 'sentence_transformers')` to define a dedicated cache directory for the embedding model.

### Verification

After this change, the application should:
*   Successfully load the `sentence-transformers/all-MiniLM-L6-v2` model.
*   Generate valid embeddings.
*   Allow `MemoryReaderNode` to perform successful vector searches, leading to populated `merged` dictionaries in `JoinNode`s and correct variable assignments downstream.

