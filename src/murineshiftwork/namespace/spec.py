"""Re-export the acquisition-namespace core for backwards compatibility.

The canonical implementation lives in the ``acquisition_namespace`` package.
MSW-specific logic (namespace.msw.yaml, msw_file, get_msw_builder) stays here.
"""

from acquisition_namespace import NamespaceBuilder, NamespaceLevelSpec, NamespaceSpec
from acquisition_namespace.spec import _template_fields

__all__ = [
    "NamespaceBuilder",
    "NamespaceLevelSpec",
    "NamespaceSpec",
    "_template_fields",
]
