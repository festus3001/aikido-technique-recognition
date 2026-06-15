# tools/

Project tooling that is not part of the builder/contributor/web application surfaces.

## crawler/
The lineage and federation data-map crawler. Populates data/map/ with normalized JSON for
people, organizations, dojos, rank events, and lineage edges, from authoritative sources --
chiefly the annual Aikikai Kagamibiraki promotion lists plus federation rosters and dojo
sites. Full schema, source priority, crawl plan, and the agent prompt are in
docs/atr_13_datamap_crawl. The crawler writes to ../../data/map/.
