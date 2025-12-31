# 🔷 FAISS — Full Mathematical Deep Dive & Implementation Guide

FAISS (Facebook AI Similarity Search) enables **nearest-neighbor search** across **millions → billions** of vectors for:
- Semantic Search (RAG systems)
- Image / face search
- Recommender systems

---

## 🧠 Vector Math

### Representation
Each data item is a vector:

\[
x \in \mathbb{R}^d
\]

Dataset:

\[
X = \{x_1, x_2, ..., x_n\} \in \mathbb{R}^{n \times d}
\]

---

## 🔢 Distance Metrics

### Euclidean (L2)
\[
D(x,q) = \| x - q \|^2 = \sum_{i=1}^{d} (x_i - q_i)^2
\]

### Cosine Similarity
\[
\cos(x,q) = \frac{x \cdot q}{\|x\| \|q\|}
\]

FAISS normalizes vectors → converts cosine → L2.

---

## 🚀 Why FAISS is Needed

Naive search:

\[
O(n \cdot d)
\]

Example: n = 1B vectors, d = 768 → **too slow**

---

## 🏗 FAISS Acceleration Strategies

### 1️⃣ IVF — Inverted File Index
Cluster space using k-means:

\[
\mu_1, \ldots, \mu_K
\]

Assign:

\[
bucket(x) = argmin_j \|x - \mu_j\|
\]

Search only within nearest buckets:

\[
O((n/K) \cdot d)
\]

---

### 2️⃣ PQ — Product Quantization

Split vector:

\[
x = [x^{(1)}, \ldots, x^{(m)}]
\]

Quantize each:

\[
x^{(j)} ≈ c_{a_j}^{(j)}
\]

Distance lookup-table approximation:

\[
D(q, x) ≈ \sum_{j=1}^{m} \| q^{(j)} - c_{a_j}^{(j)} \|
\]

Storage reduces by ~97%.

---

### 3️⃣ HNSW — Graph-Based Search

\[
O(\log n)
\]

Small-world graph — walks greedily toward neighbors.

---

## 🧪 RAG Architecture (Semantic Search)

