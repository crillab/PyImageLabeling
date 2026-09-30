"""Mixed-precision helper for the SAM hot path.

Automatic mixed precision (FP16 compute, FP32 master weights) on CUDA:
~1.5-2x faster forwards and halved activation memory. No-op on CPU.
All call sites validate numerically (masks must be unchanged).
"""

import contextlib


@contextlib.contextmanager
def cuda_autocast(device):
    """Yield inside torch.autocast(fp16) when device is CUDA, else plain."""
    if device == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                with torch.autocast(device_type="cuda",
                                    dtype=torch.float16):
                    yield
                return
        except Exception:
            pass
    yield
