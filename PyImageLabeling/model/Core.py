# Backward-compat shim for the pre-refactor namespace.
from PyImageLabeling.model.Base import Base
from PyImageLabeling.model.Base import *  # noqa: F401,F403
Core = Base
