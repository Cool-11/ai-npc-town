"""Monkey-patch for hello-agents 0.2.9.

Three issues fixed:
  1. create_embedding_model passes model_name kwarg to TFIDFEmbedding -> TypeError.
  2. QdrantConnectionManager raises ImportError without qdrant-client.
     Patched with an in-memory TF-IDF-backed vector store (when QDRANT_DISABLED=true).
     Returns hits in the format episodic.py expects: {"metadata": {...}, "score": float}.
  3. TFIDFEmbedding is never fit by hello-agents, so encode() throws.
     We scan memory_data/*.db on first embedder build and fit with all existing memories.
"""

import os as _os
import sqlite3 as _sqlite3
import threading as _threading
from pathlib import Path as _Path
from math import sqrt as _sqrt

import hello_agents.memory.embedding as _emb_mod

# ============================================================
# Patch 1: filter unsupported kwargs per embedder type
# ============================================================
_orig_create_embedding_model = _emb_mod.create_embedding_model

def _patched_create_embedding_model(model_type, **kwargs):
    if model_type in ('local', 'sentence_transformer', 'huggingface'):
        kwargs.pop('api_key', None)
        kwargs.pop('base_url', None)
    elif model_type == 'dashscope':
        pass
    elif model_type == 'tfidf':
        kwargs.pop('model_name', None)
        kwargs.pop('api_key', None)
        kwargs.pop('base_url', None)
    return _orig_create_embedding_model(model_type, **kwargs)

_emb_mod.create_embedding_model = _patched_create_embedding_model

# ============================================================
# Patch 2: in-memory TF-IDF vector store (replaces Qdrant when disabled)
# ============================================================
class _InMemoryTFIDFVectorStore:
    def __init__(self):
        self._lock = _threading.RLock()
        self._index = {}
        self._embedder = None
        self._memory_data_dir = _Path(__file__).parent / 'memory_data'
        self._seed_loaded = False

    def _get_embedder(self):
        if self._embedder is None:
            self._embedder = _emb_mod.get_text_embedder()
        return self._embedder

    def _load_existing_memories(self):
        if self._seed_loaded:
            return
        with self._lock:
            if self._seed_loaded:
                return
            self._seed_loaded = True
            embedder = self._get_embedder()
            count = 0
            for db_path in self._memory_data_dir.rglob('memory.db'):
                try:
                    con = _sqlite3.connect(str(db_path))
                    for row in con.execute(
                        "SELECT id, content, user_id, memory_type, importance, timestamp FROM memories WHERE content IS NOT NULL AND content != ''"
                    ).fetchall():
                        mem_id, content_text, user_id, mem_type, importance, ts = row
                        try:
                            vec = embedder.encode(content_text)
                            if hasattr(vec, 'tolist'):
                                vec = vec.tolist()
                            self._index[mem_id] = {
                                'vector': vec,
                                'metadata': {
                                    'memory_id': mem_id,
                                    'memory_type': mem_type,
                                    'user_id': user_id,
                                    'importance': importance,
                                    'timestamp': ts,
                                    'content': content_text,
                                },
                            }
                            count += 1
                        except Exception:
                            pass
                    con.close()
                except Exception:
                    pass
            if count:
                print(f'[patch] vector index seeded with {count} historical memories')

    def add_vectors(self, vectors=None, metadata=None, ids=None, **kwargs):
        self._load_existing_memories()
        with self._lock:
            vectors = list(vectors or [])
            metadata = list(metadata or [])
            ids = list(ids or [])
            for i, vec in enumerate(vectors):
                meta = dict(metadata[i]) if i < len(metadata) else {}
                mem_id = ids[i] if i < len(ids) else meta.get('memory_id') or meta.get('id')
                if not mem_id or vec is None:
                    continue
                if hasattr(vec, 'tolist'):
                    vec = vec.tolist()
                self._index[mem_id] = {'vector': vec, 'metadata': meta}

    def search_similar(self, query_vector, limit=10, score_threshold=None, where=None):
        self._load_existing_memories()
        with self._lock:
            q = list(query_vector)
            q_norm = _sqrt(sum(x*x for x in q)) or 1.0
            scored = []
            for mem_id, entry in self._index.items():
                v = entry['vector']
                meta = entry['metadata']
                if v is None or len(v) != len(q):
                    continue
                if where:
                    skip = False
                    for k, val in where.items():
                        if meta.get(k) != val:
                            skip = True
                            break
                    if skip:
                        continue
                dot = sum(a*b for a, b in zip(q, v))
                v_norm = _sqrt(sum(x*x for x in v)) or 1.0
                score = dot / (q_norm * v_norm)
                scored.append((score, meta))
            scored.sort(key=lambda x: x[0], reverse=True)
            if score_threshold is not None:
                scored = [(s, m) for s, m in scored if s >= score_threshold]
            return [{'metadata': meta, 'score': s} for s, meta in scored[:limit]]

    def delete_memories(self, memory_ids):
        with self._lock:
            for mem_id in memory_ids:
                self._index.pop(mem_id, None)

    def get_collection_stats(self):
        with self._lock:
            return {'store_type': 'in_memory_tfidf', 'points_count': len(self._index)}

    def count(self, *a, **k):
        return len(self._index)

    def upsert(self, *a, **k):
        return self.add_vectors(*a, **k)

    def search(self, *a, **k):
        return self.search_similar(*a, **k)

    def get(self, *a, **k):
        return None


if _os.getenv('QDRANT_DISABLED', '').lower() in ('1', 'true', 'yes'):
    try:
        from hello_agents.memory.storage.qdrant_store import QdrantConnectionManager as _QCM
        @classmethod
        def _patched_get_instance(cls, **kwargs):
            return _InMemoryTFIDFVectorStore()
        _QCM.get_instance = _patched_get_instance
    except Exception:
        pass

# ============================================================
# Patch 3: auto-fit TF-IDF on first embedder build
# ============================================================
def _collect_memory_corpus(memory_data_dir):
    corpus = []
    if not memory_data_dir.exists():
        return corpus
    for db_path in memory_data_dir.rglob('memory.db'):
        try:
            con = _sqlite3.connect(str(db_path))
            for (text,) in con.execute(
                "SELECT content FROM memories WHERE content IS NOT NULL AND content != ''"
            ).fetchall():
                corpus.append(text)
            con.close()
        except Exception:
            pass
    return corpus

_orig_build = _emb_mod._build_embedder

def _patched_build():
    embedder = _orig_build()
    if isinstance(embedder, _emb_mod.TFIDFEmbedding) and not embedder._is_fitted:
        memory_data = _Path(__file__).parent / 'memory_data'
        corpus = _collect_memory_corpus(memory_data)
        if corpus:
            try:
                embedder.fit(corpus)
                print(f'[patch] TF-IDF fitted on {len(corpus)} existing memories (dim={embedder.dimension})')
            except Exception as ex:
                print(f'[patch] TF-IDF fit failed: {ex}')
        else:
            print('[patch] TF-IDF: no memories yet, embedder stays unfit (encode will fail until retrained)')
    return embedder

_emb_mod._build_embedder = _patched_build


# ============================================================
# Patch 4: TFIDFEmbedding use char-level analyzer (works for Chinese)
# ============================================================
import hello_agents.memory.embedding as _emb_mod_full
from sklearn.feature_extraction.text import TfidfVectorizer as _TV
_orig_init_vectorizer = _emb_mod_full.TFIDFEmbedding._init_vectorizer


def _patched_init_vectorizer(self):
    self._vectorizer = _TV(
        max_features=self.max_features,
        analyzer='char_wb',
        ngram_range=(2, 4),
    )


_emb_mod_full.TFIDFEmbedding._init_vectorizer = _patched_init_vectorizer


# ============================================================
# Patch 5: EpisodicMemory.retrieve filter by NPC user_id
# Without this, our global vector store returns hits from other NPCs
# which get dropped because doc_store.get_memory() cant find them.
# ============================================================
from hello_agents.memory.types import episodic as _episodic_mod

_orig_retrieve = _episodic_mod.EpisodicMemory.retrieve


def _patched_retrieve(self, query, limit=5, **kwargs):
    """Patched retrieve: inject user_id (NPC name) into where filter and importance_threshold."""
    # Force user_id from this NPC's identity so vector store hits match this NPC's memories.
    npc_user_id = getattr(self, 'user_id', None) or kwargs.get('user_id')
    if npc_user_id and 'user_id' not in kwargs:
        kwargs['user_id'] = npc_user_id
    # Also translate min_importance -> importance_threshold so episodic.py actually applies it
    if 'min_importance' in kwargs and 'importance_threshold' not in kwargs:
        kwargs['importance_threshold'] = kwargs.pop('min_importance')
    return _orig_retrieve(self, query, limit, **kwargs)


_episodic_mod.EpisodicMemory.retrieve = _patched_retrieve
