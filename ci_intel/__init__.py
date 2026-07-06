"""ci_intel -- intelligence helpers for the OpenCV CI system.

Phase 1 ships :mod:`ci_intel.scheduler`, a pure-Python matcher that maps
``priority:*`` pull-request labels to the workflow files that should be
dispatched first. It has no GitHub or workflow-file dependencies.
"""

__all__ = ["scheduler"]
