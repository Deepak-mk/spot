#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAISS Example — Index Creation, Search, Save/Load
"""

import faiss
import numpy as np
import os

# -------------------------------
# 1️⃣ CREATE SAMPLE VECTOR DATA
# -------------------------------
dimension = 128                          # size of each embedding
num_vectors = 50000                      # pretend we have 50k documents
data = np.random.random((num_vectors, dimension)).astype('float32')

# -------------------------------
# 2️⃣ DEFINE INDEX TYPE
# IVF=partition, PQ=compression
# -------------------------------
nlist = 100                              # number of clusters
m = 16                                   # PQ subvectors
nbits = 8                                # bits per PQ code

index = faiss.IndexIVFPQ(dimension, nlist, m, nbits)
quantizer = faiss.IndexFlatL2(dimension) # base quantizer
index = faiss.IndexIVFPQ(dimension, nlist, m, nbits)

# -------------------------------
# 3️⃣ TRAIN INDEX (REQUIRED)
# -------------------------------
index.train(data)
index.add(data)

# -------------------------------
# 4️⃣ RUN SEARCH
# -------------------------------
query = np.random.random((1, dimension)).astype('float32')
index.nprobe = 8  # probes for accuracy vs speed
distances, ids = index.search(query, 5)

print("🔍 Top-5 Results:\n", list(zip(ids.tolist()[0], distances.tolist()[0])))

# -------------------------------
# 5️⃣ SAVE / LOAD INDEX
# -------------------------------
save_path = "./faiss.index"
faiss.write_index(index, save_path)
print("💾 Saved index:", save_path)

loaded = faiss.read_index(save_path)
print("📂 Reloaded index — OK:", type(loaded))
