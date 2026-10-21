import json
from src.config import config
from src.schemas.study import Concept, RagChunk

def retrieve(concept_id: str) -> list[RagChunk]:
    return [
        RagChunk(
            id="fake-1",
            concept_id=concept_id,
            text="The chain rule says (f(g(x)))' = f'(g(x)) * g'(x).",
            book="Calculus Vol. 1",
            section="3.6 The Chain Rule",
            score=0.9,
        )
    ]

def load_concept_map() -> list[Concept]:
    with open(config.concept_map_path, encoding="utf-8") as f:
        data = json.load(f)
    return [Concept(**item) for item in data]

"""
Optional project capability: Retrieval-Augmented Generation (RAG).

Implement this module only if this capability is relevant to your application's
user problem. Remove the file if the capability is not used.

Conceptual Overview:
-------------------
Retrieval-Augmented Generation (RAG) enhances model responses by retrieving
relevant external information before passing the prompt to the LLM.

Key concepts to consider when implementing RAG:
1. Document Ingestion: Loading custom domain documents (PDFs, text, markdown).
2. Embeddings & Vector Store: Converting text into dense vector embeddings and
   storing them in a vector database or local index.
3. Retrieval: Searching the vector store for text chunks semantically similar
   to the user query.
4. Grounding: Constructing a prompt that supplies retrieved context to the model,
   reducing hallucinations and grounding answers in verified factual data.

Note:
-----
Do not implement RAG unless your project requires answering questions over
specific custom documents or static domain knowledge bases.
"""

# Implement custom RAG pipeline below if selected for your project.
