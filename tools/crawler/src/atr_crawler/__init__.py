"""ATR lineage and federation data-map crawler.

Builds a normalized, provenance-stamped graph of aikido organizations, dojos,
people, ranks, tenures, and lineage edges. See docs/atr_13_datamap_crawl.md for
the full specification and tools/crawler/schema/entities.schema.json for the
data contract.

The crawler is idempotent: every record carries a stable slug id, so re-runs
merge rather than duplicate. Promotion lists are the backbone for the recent
decades; tenure and co-presence reconstruct the earlier ones.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
