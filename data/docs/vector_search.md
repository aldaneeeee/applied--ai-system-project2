# Embeddings and Vector Search

Vector search is the retrieval engine behind most RAG systems. It represents
text as numeric vectors and finds passages whose vectors are closest to the
vector of the query.

## Embeddings

An embedding is a fixed-length vector of numbers that represents the meaning of
a piece of text. Texts with similar meaning have vectors that point in similar
directions. Dense embeddings are produced by neural networks, while sparse
representations such as TF-IDF are produced by counting term frequencies.

## TF-IDF

TF-IDF stands for Term Frequency-Inverse Document Frequency. It scores a term
highly in a document when the term appears often in that document (term
frequency) but rarely across the whole collection (inverse document frequency).
TF-IDF is a sparse, transparent representation that needs no training data and
no model downloads, which makes it easy to run locally and fully reproducible.

## Cosine similarity

Cosine similarity measures how close two vectors are by taking the cosine of the
angle between them. A cosine similarity of 1 means the vectors point in exactly
the same direction, and 0 means they are unrelated. Retrieval ranks candidate
passages by their cosine similarity to the query and returns the top matches.

## Top-k retrieval

Top-k retrieval means returning the k highest-scoring passages for a query. A
larger k gives the model more context but increases the chance of including
irrelevant text; a smaller k is more focused but risks missing a relevant
passage. Choosing k is a trade-off tuned for each application.
