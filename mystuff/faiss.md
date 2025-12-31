# 🔷 What is FAISS?

**FAISS (Facebook AI Similarity Search)** is a vector search library that enables **fast nearest-neighbor search at scale** (millions to billions of embeddings).

👉 It answers:  
**Given a query vector, which vectors in the database are most similar?**

### 🏁 Used in:

- ChatGPT / RAG search engines
- Recommendation systems
- Image search
- Semantic search on embeddings
- Clustering 100M+ vectors efficiently

---

# 🧠 Mathematical Foundation

## 1️⃣ Data Representation

All input data must be vectors in **d-dimensional space**:

\[
x \in \mathbb{R}^d
\]

Example: OpenAI text-embedding (1536-dim) → **d = 1536**

FAISS stores a matrix:

\[
X =
\begin{bmatrix}
x_1^T \\
x_2^T \\
\vdots \\
x_n^T
\end{bmatrix}
\]

Where:

- **n** = number of records (millions → billions)

---

## 2️⃣ Similarity Metrics

FAISS supports two main distance functions:

### 🟡 L2 (Euclidean) Distance
Most common for raw numeric vectors:

\[
D(x, q) = \|x - q\|_2^2 = \sum_{i=1}^{d} (x_i - q_i)^2
\]

📌 Lower distance → more similar

---

### 🔵 Cosine Similarity
Used for embeddings (semantic meaning):

\[
\cos(x, q) = \frac{x \cdot q}{\|x\| \|q\|}
\]

FAISS internally **normalizes vectors** and converts cosine → equivalent L2 search:

\[
\text{cosine distance} = 2 - 2 \cdot \cos(x,q)
\]

So **FAISS always performs L2 math under the hood**.

---

## 3️⃣ Naïve Nearest Neighbor Complexity

Brute-force search requires computing:

\[
D(q, x_i) \quad \forall i = 1 \dots n
\]

Time complexity:

\[
O(n \cdot d)
\]

For **1B vectors** (d=768) → **TOO SLOW** ⛔  
⚠️ This is why FAISS introduces **indexing**, **quantization**, **compression**, **clustering**.

---

# ⚙️ How FAISS Becomes Fast

| Component          | Idea                                           |
|-------------------|------------------------------------------------|
| IndexFlatL2       | Exact search (slowest but simplest)            |
| IVF               | Vector-space partitioning w/ k-means clusters  |
| PQ                | Compress vectors into few bytes                |
| HNSW              | Graph-based approximate NN search              |
| GPU Acceleration  | CUDA kernels → compute billions of distances   |

---

# 🔶 1️⃣ IVF (Inverted File Index) — Cluster-Based Search

FAISS performs **k-means** to produce **K centroids**:

\[
\mu_1, \mu_2, \dots, \mu_K
\]

Each stored vector is assigned:

\[
\text{bucket}(x) = \arg\min_j \|x - \mu_j\|^2
\]

🟩 Instead of comparing query against **all vectors**, FAISS **searches only inside closest buckets** (controlled by `nprobe`).

### Complexity reduction:

\[
O(n \cdot d) \rightarrow O\left(\frac{n}{K} \cdot d\right)
\]

---

# 🔶 2️⃣ PQ — Product Quantization (Compression + Fast Distance)

Divide each vector into **m** subvectors:

\[
x = [x^{(1)}, x^{(2)}, ..., x^{(m)}]
\]

For each segment, FAISS learns **k quantizers** via k-means:

\[
C_j = \{c_1^{(j)}, ..., c_k^{(j)}\}
\]

Then the vector is represented **as integer codes instead of floats**:

\[
x \approx [c_{a_1}^{(1)}, ..., c_{a_m}^{(m)}]
\]

📉 Storage reduces by **~97%**  
*(1536 floats → ≈128 bits)*

Distance becomes **lookup-table-based**:

\[
D(q, x) \approx \sum_{j=1}^{m} \|q^{(j)} - c_{a_j}^{(j)}\|^2
\]

Complexity becomes:

\[
O(m) \quad \text{instead of} \quad O(d)
\]

---

# 🔷 3️⃣ HNSW (Graph Search)

FAISS can use **Hierarchical Navigable Small-World Graphs**  
Each vector is a **node**, edges connect neighbors.

Search algorithm:

1️⃣ Start at a random node  
2️⃣ Walk greedily toward closest neighbor  
3️⃣ Narrow search locally  

Average time complexity:

\[
O(\log n)
\]

---

# 🧪 Example Workflow

### 📍 Create Index

```python
import faiss
import numpy as np

d = 768
vectors = np.random.rand(1_000_000, d).astype('float32')
index = faiss.IndexIVFPQ(d, nlist=1000, m=64, nbits=8)

index.train(vectors)
index.add(vectors)


| Feature   | Math                    | Benefit                    |
| --------- | ----------------------- | -------------------------- |
| L2 Search | ∑(xi​−qi​)2               | Exact Nearest Neighbor     |
| Cosine    | (x ⋅ q / (|x| |q|))     | Semantic Similarity        |
| IVF       | k-means clusters        | Search inside only buckets |
| PQ        | Quantization + LUT sum  | Compress vectors 100×      |
| HNSW      | Graph NN                | (O(log n)) fast search    |
| GPU       | CUDA kernel compute     | Billion-scale real-time    |


| Abbrev. | Full Form                                | Meaning (1-Line)                                                       |
| ------- | ---------------------------------------- | ---------------------------------------------------------------------- |
| FAISS   | Facebook AI Similarity Search            | Library to search similar vectors fast (like "Google for embeddings"). |
| NN      | Nearest Neighbor                         | Find the closest vector/document to a query.                           |
| d       | Dimension                                | Size of each embedding vector (e.g., 768, 1536).                       |
| L2      | Euclidean Distance                       | Straight-line distance between vectors; used to measure similarity.    |
| COS     | Cosine Similarity                        | Angle-based similarity; used in semantic search.                       |
| IVF     | Inverted File Index                      | Clusters vectors → search only inside top buckets (faster).            |
| K-Means | –                                        | Algorithm used to make clusters (centroids) inside FAISS.              |
| PQ      | Product Quantization                     | Compress vectors into tiny codes → use lookup tables for speed.        |
| LUT     | Lookup Table                             | Pre-computed table used to calculate distances faster.                 |
| m       | PQ Subvectors Count                      | How many pieces a vector is split into for PQ compression.             |
| K       | Number of Clusters                       | IVF parameter — more clusters = more accuracy, slower search.          |
| nprobe  | Probes Count                             | How many IVF clusters to check during search.                          |
| HNSW    | Hierarchical Navigable Small-World Graph | Graph-based index → very fast approximate search.                      |
| GPU     | Graphics Processing Unit                 | FAISS can use GPU for massive-scale fast search.                       |

Like putting books into labeled shelves — and when you want one, you only check the right shelf instead of searching the entire library.
