"""Workflow scheduling helpers.

Public API for Phase 1 (priority-label matching)::

    from ci_intel.scheduler import LabelMatcher
    result = LabelMatcher.from_config().prioritize(pr_labels, workflow_names)
"""

from .labels import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_PRIORITY_PREFIX,
    LabelMatcher,
    PrioritizationResult,
    prioritize_workflows,
)

__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_PRIORITY_PREFIX",
    "LabelMatcher",
    "PrioritizationResult",
    "prioritize_workflows",
]
