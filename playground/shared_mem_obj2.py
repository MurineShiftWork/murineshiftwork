import multiprocessing as mp

import numpy as np

data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
d_shape = (len(data),)
d_type = np.int64
d_size = np.dtype(d_type).itemsize * np.prod(d_shape)

# In main process
# allocate new shared memory
shm = mp.shared_memory.SharedMemory(create=True, size=d_size)
shm_name = shm.name
# numpy array on shared memory buffer
a = np.ndarray(shape=d_shape, dtype=d_type, buffer=shm.buf)
# copy data into shared memory ndarray once
a[:] = data[:]

# In other processes
# reuse existing shared memory
ex_shm = mp.shared_memory.SharedMemory(name=shm_name)
# numpy array on existing memory buffer, a and b read/write the same memory
b = np.ndarray(shape=d_shape, dtype=d_type, buffer=ex_shm.buf)
ex_shm.close()  # close after using

# In main process
shm.close()  # close after using
shm.unlink()  # free memory
