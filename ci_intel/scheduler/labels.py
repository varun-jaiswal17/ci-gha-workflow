#!/usr/bin/env python3

"""
Priority-label matching for OpenCV CI workflows (Phase 1).

When a reviewer adds a label such as ``priority:windows`` to a pull request the
CI system should dispatch the matching platform workflows before the rest. This
module is the pure-Python core of that feature: given a set of PR label names
and a list of workflow file names it decides which workflows are *prioritised*.

It performs no GitHub API calls and reads no workflow files. The routing table
lives in ``config.yaml`` next to the ``ci_intel`` package (see
:data:`DEFAULT_CONFIG_PATH`) and maps each priority label to a list of keywords:

    label_platform_map:
      priority:windows: ['W10', 'Win', 'Windows']
      priority:ALL:     null        # null == match every workflow

A workflow matches a label when any of that label's keywords is a
case-insensitive **substring** of the workflow file name. A ``null`` keyword
list is the wildcard (``priority:ALL``) and matches every workflow.

Typical use::

    matcher = LabelMatcher.from_config()
    result = matcher.prioritize(pr_labels, workflow_file_names)
    dispatch_order = result.ordered  # prioritised workflows first, then the rest
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


# config.yaml lives at the package root (one level up from this `scheduler` pkg).
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

# Labels are only considered for prioritisation when they carry this prefix.
DEFAULT_PRIORITY_PREFIX = "priority:"


def _workflow_name(workflow: str) -> str:
    """Return the lower-cased base file name used for substring matching."""
    return Path(workflow).name.lower()


@dataclass(frozen=True)
class PrioritizationResult:
    """The outcome of matching a PR's labels against a list of workflows."""

    #: Label keys that matched the routing table, in first-seen order, deduped
    #: (original casing from the config, e.g. ``"priority:windows"``).
    requested: tuple[str, ...]
    #: ``priority:*`` labels that were not found in the routing table.
    unknown: tuple[str, ...]
    #: Workflows matching at least one requested label, in input order.
    prioritized: tuple[str, ...]
    #: Workflows matching none of the requested labels, in input order.
    deprioritized: tuple[str, ...]
    #: Per-label breakdown: label key -> matching workflows (input order).
    matched_by: dict[str, tuple[str, ...]]
    #: True if a wildcard label (keyword list ``null``, e.g. priority:ALL) ran.
    match_all: bool = False

    @property
    def ordered(self) -> list[str]:
        """All workflows with the prioritised ones first; stable within each group."""
        return [*self.prioritized, *self.deprioritized]


class LabelMatcher:
    """Maps ``priority:*`` PR labels to the workflows that should run first.

    The routing table is a mapping of label -> keyword list. Matching is a
    case-insensitive substring test of each keyword against the workflow file
    name. A ``None`` keyword list is a wildcard that matches every workflow.
    """

    def __init__(
        self,
        label_platform_map: dict[str, list[str] | None],
        priority_prefix: str = DEFAULT_PRIORITY_PREFIX,
    ) -> None:
        self.priority_prefix = priority_prefix

        # Normalise for case-insensitive lookup/matching while remembering the
        # original key casing for reporting.
        self._keywords: dict[str, tuple[str, ...] | None] = {}
        self._original_key: dict[str, str] = {}
        for key, keywords in label_platform_map.items():
            norm = key.strip().lower()
            self._original_key[norm] = key
            if keywords is None:
                self._keywords[norm] = None  # wildcard (match all)
            else:
                self._keywords[norm] = tuple(kw.lower() for kw in keywords)

    @classmethod
    def from_config(cls, path: str | Path | None = None) -> "LabelMatcher":
        """Build a matcher from a ``config.yaml`` (defaults to the bundled one)."""
        config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return cls(data.get("label_platform_map") or {})

    @property
    def labels(self) -> tuple[str, ...]:
        """The label keys known to the routing table (original casing)."""
        return tuple(self._original_key.values())

    def is_priority_label(self, label: str) -> bool:
        """True if ``label`` carries the configured ``priority:`` prefix."""
        return bool(label) and label.strip().lower().startswith(
            self.priority_prefix.lower()
        )

    def keywords_for_label(self, label: str) -> tuple[str, ...] | None:
        """Return the keyword tuple for ``label`` (``None`` for a wildcard label).

        Raises :class:`KeyError` if the label is not in the routing table; use
        :meth:`is_known_label` to check first when that matters.
        """
        return self._keywords[label.strip().lower()]

    def is_known_label(self, label: str) -> bool:
        """True if ``label`` is present in the routing table (case-insensitive)."""
        return label.strip().lower() in self._keywords

    def matches(self, label: str, workflow: str) -> bool:
        """True if ``workflow`` matches ``label``'s keywords (or label is wildcard)."""
        keywords = self.keywords_for_label(label)
        if keywords is None:  # wildcard, e.g. priority:ALL
            return True
        name = _workflow_name(workflow)
        return any(kw in name for kw in keywords)

    def prioritize(
        self,
        labels: list[str] | tuple[str, ...],
        workflows: list[str] | tuple[str, ...],
    ) -> PrioritizationResult:
        """Partition ``workflows`` by the priority labels on a PR.

        A workflow is *prioritised* if it matches any requested label. Ordering
        within both the prioritised and de-prioritised groups follows the input
        ``workflows`` order, so the result is fully deterministic.
        """
        requested: list[str] = []
        unknown: list[str] = []
        match_all = False
        seen: set[str] = set()
        for label in labels:
            if not self.is_priority_label(label):
                continue  # not a priority label (e.g. category:* gating labels)
            norm = label.strip().lower()
            if norm not in self._keywords:
                unknown.append(label.strip())
            elif norm not in seen:
                seen.add(norm)
                requested.append(self._original_key[norm])
                if self._keywords[norm] is None:
                    match_all = True

        # Pre-lower each workflow name once.
        named = [(wf, _workflow_name(wf)) for wf in workflows]

        def label_hits(norm_label: str) -> tuple[str, ...]:
            keywords = self._keywords[norm_label]
            if keywords is None:
                return tuple(wf for wf, _ in named)
            return tuple(wf for wf, name in named if any(kw in name for kw in keywords))

        matched_by = {key: label_hits(key.strip().lower()) for key in requested}

        # A workflow is prioritised if any requested label matched it. Building a
        # union set keeps each workflow once even if several labels matched it.
        prioritized_set = set()
        for hits in matched_by.values():
            prioritized_set.update(hits)

        prioritized: list[str] = []
        deprioritized: list[str] = []
        for wf, _ in named:
            (prioritized if wf in prioritized_set else deprioritized).append(wf)

        return PrioritizationResult(
            requested=tuple(requested),
            unknown=tuple(unknown),
            prioritized=tuple(prioritized),
            deprioritized=tuple(deprioritized),
            matched_by=matched_by,
            match_all=match_all,
        )


def prioritize_workflows(
    labels: list[str] | tuple[str, ...],
    workflows: list[str] | tuple[str, ...],
    config_path: str | Path | None = None,
) -> PrioritizationResult:
    """One-shot helper: build a matcher from config and prioritise ``workflows``."""
    return LabelMatcher.from_config(config_path).prioritize(labels, workflows)
