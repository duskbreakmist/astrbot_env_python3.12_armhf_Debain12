import json, os, platform, sys, tempfile
import numpy as np
import faiss
faiss.omp_set_num_threads(1)
rng=np.random.default_rng(12345)
x=rng.random((512,16),dtype=np.float32)
q=x[:12].copy()
truth=((q[:,None,:]-x[None,:,:])**2).sum(axis=2)
expected=np.argsort(truth,axis=1)[:,:5]
flat=faiss.IndexFlatL2(16); flat.add(x)
d,i=flat.search(q,5)
np.testing.assert_array_equal(i,expected)
np.testing.assert_allclose(d,np.take_along_axis(truth,expected,axis=1),atol=2e-5)
ids=np.arange(len(x),dtype=np.int64)+3_000_000_000
mapped=faiss.IndexIDMap2(faiss.IndexFlatL2(16)); mapped.add_with_ids(x,ids)
_,mi=mapped.search(q,5); np.testing.assert_array_equal(mi,ids[expected])
np.testing.assert_allclose(mapped.reconstruct(int(ids[0])),x[0])
for index in (flat,mapped):
    restored=faiss.deserialize_index(faiss.serialize_index(index))
    np.testing.assert_array_equal(index.search(q,5)[1],restored.search(q,5)[1])
ivf=faiss.IndexIVFFlat(faiss.IndexFlatL2(16),16,4)
ivf.train(x); ivf.add_with_ids(x,ids); ivf.nprobe=4
np.testing.assert_array_equal(ivf.search(q,5)[1],ids[expected])
restored=faiss.deserialize_index(faiss.serialize_index(ivf))
np.testing.assert_array_equal(restored.search(q,5)[1],ids[expected])
# Exercise Python virtual callbacks as well as the statically linked core.
selector=faiss.PyCallbackIDSelector(lambda idx: idx % 2 == 0)
removed=faiss.clone_index(mapped)
assert removed.remove_ids(selector)==256
assert removed.ntotal==256
assert np.all(removed.search(q,5)[1] % 2 == 1)
hnsw=faiss.IndexHNSWFlat(16,8); hnsw.add(x)
assert np.array_equal(hnsw.search(q,1)[1][:,0],np.arange(len(q)))
with tempfile.TemporaryDirectory(prefix="faiss-armhf-") as tmp:
    disk=faiss.OnDiskInvertedLists(2,4,os.path.join(tmp,"lists.bin"))
    disk_ids=np.array([3_000_000_001,3_000_000_002,3_000_000_003],dtype=np.int64)
    codes=np.arange(12,dtype=np.uint8)
    disk.add_entries(0,3,faiss.swig_ptr(disk_ids),faiss.swig_ptr(codes))
    np.testing.assert_array_equal(faiss.rev_swig_ptr(disk.get_ids(0),3),disk_ids)
    disk.resize(0,2); assert disk.list_size(0)==2
    disk.resize(0,0); assert disk.list_size(0)==0
    disk.resize(1,16); disk.resize(1,0)
    del disk
print(json.dumps(dict(status="PASS",faiss=faiss.__version__,numpy=np.__version__,python=sys.version, machine=platform.machine(),pointer_bytes=np.dtype(np.uintp).itemsize,faiss_file=faiss.__file__,tests=["FlatL2 vs NumPy", "64-bit IDs above 2^31", "reconstruct", "Flat/IDMap/IVF serialization", "IVFFlat training and search", "C++ to Python selector callback", "HNSW", "OnDiskInvertedLists allocate/shrink/free"]),indent=2))
