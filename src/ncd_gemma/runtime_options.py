"""Request-local controls; never mutate the shared agent or global settings."""
from contextvars import ContextVar

use_cache = ContextVar('use_cache', default=True)
use_reranker = ContextVar('use_reranker', default=True)
