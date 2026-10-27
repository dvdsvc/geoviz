"""Incremental embedding script: only embed texts not already in cache."""
import sys, os, time, json
sys.path.insert(0, 'data/private/ai_workspace')
sys.path.insert(0, 'backend')
os.chdir('backend')

from sample_loader import load_samples, sample_to_text
from gemini_embedding import embed_batch, _text_hash, _get_cache_conn
import chromadb
from chromadb.config import Settings as ChromaSettings
from collections import Counter

samples = load_samples()
print(f'Total: {len(samples)}')

# Build texts and IDs
sid_counts = Counter(s['sampleId'] for s in samples)
dup_sids = {k for k, v in sid_counts.items() if v > 1}

texts = []; ids = []; metadatas = []
for s in samples:
    sid = s['sampleId']
    if sid in dup_sids:
        age = s.get('ageMa')
        sid = f'{sid}_{age}' if age is not None else sid
    texts.append(sample_to_text(s))
    ids.append(sid)
    metadatas.append({
        'sampleId': s['sampleId'], 'region': s.get('region', ''),
        'basin': s.get('basin', ''), 'formation': s.get('formation', ''),
        'rockType': s.get('rockType', ''),
        'ageMa': str(s.get('ageMa', '')) if s.get('ageMa') is not None else '',
    })

# Check which texts are already cached
conn = _get_cache_conn()
cached = set()
for i, t in enumerate(texts):
    h = _text_hash(t)
    row = conn.execute("SELECT embedding FROM embed_cache WHERE text_hash = ?", (h,)).fetchone()
    if row is not None:
        cached.add(i)

uncached = [i for i in range(len(texts)) if i not in cached]
print(f'Cached: {len(cached)}, need embed: {len(uncached)}')

# Embed only uncached, in small batches
batch_size = 20
done = 0
for batch_start in range(0, len(uncached), batch_size):
    batch_indices = uncached[batch_start:batch_start + batch_size]
    batch_texts = [texts[i] for i in batch_indices]
    batch_num = batch_start // batch_size + 1
    total_batches = (len(uncached) - 1) // batch_size + 1
    print(f'Batch {batch_num}/{total_batches}: {len(batch_texts)} texts...', end=' ', flush=True)
    embs = embed_batch(batch_texts, use_cache=True)
    done += len(embs)
    print(f'OK ({done}/{len(uncached)})')
    if batch_start + batch_size < len(uncached):
        delay = 20
        print(f'  sleep {delay}s...')
        time.sleep(delay)

# Now all texts are cached; build full embedding list from cache
all_embeddings = []
for i, t in enumerate(texts):
    h = _text_hash(t)
    row = conn.execute("SELECT embedding FROM embed_cache WHERE text_hash = ?", (h,)).fetchone()
    all_embeddings.append(json.loads(row[0]))

print(f'All {len(all_embeddings)} embeddings ready')

# Save to ChromaDB
client = chromadb.PersistentClient(
    path='data/private/chroma_vectors',
    settings=ChromaSettings(anonymized_telemetry=False),
)
col = client.get_or_create_collection(
    name='geo_samples',
    metadata={'hnsw:space': 'cosine', 'dimension': 3072},
)
col.upsert(ids=ids, embeddings=all_embeddings, documents=texts, metadatas=metadatas)
print(f'DONE: {len(ids)} samples in ChromaDB')
