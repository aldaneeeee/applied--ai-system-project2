# Retrieval-Augmented Generation (RAG)

Retrieval-Augmented Generation, or RAG, is a technique for grounding a large
language model's answers in an external body of text. Instead of relying only on
the knowledge baked into the model's weights, a RAG system first *retrieves*
relevant passages from a document collection and then asks the model to generate
an answer using those passages as context.

## Why RAG is used

RAG addresses three well-known weaknesses of standalone language models:

- **Hallucination.** Because the model is instructed to answer from retrieved
  passages, it is far less likely to invent facts. When the passages do not
  contain the answer, a well-built RAG system abstains rather than guessing.
- **Stale knowledge.** A model's training data has a cutoff date. RAG lets you
  keep answers current simply by updating the document collection, with no
  retraining of the model.
- **Traceability.** Every answer can cite the passages it used, so a human can
  verify where a claim came from.

## The core RAG pipeline

A minimal RAG pipeline has three stages. First, the user's question is used to
retrieve the most relevant chunks of text from an index. Second, those chunks
are inserted into the prompt as context. Third, the model generates an answer
grounded in that context, ideally with citations back to the source chunks.

## Chunking

Documents are split into smaller pieces called chunks before they are indexed.
Chunking matters because retrieval works best on focused units of meaning: a
chunk that is too large dilutes relevance, while a chunk that is too small loses
context. A common strategy is to split on paragraph boundaries and to add a
small overlap between adjacent chunks so that a sentence spanning a boundary is
not lost.

## Grounding and abstention

A grounded answer is one whose every claim is supported by the retrieved
passages. A reliable RAG system checks grounding and, when the retrieved context
is insufficient, abstains by telling the user it does not have enough
information rather than fabricating an answer.
