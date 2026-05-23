# Graph Report - localstack-core/localstack/cloud  (2026-05-22)

## Corpus Check
- Corpus is ~814 words - fits in a single context window. You may not need a graph.

## Summary
- 41 nodes · 44 edges · 7 communities (3 shown, 4 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 4 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]

## God Nodes (most connected - your core abstractions)
1. `CloudRegistry` - 13 edges
2. `CloudProvider` - 8 edges
3. `MultiCloudEdge` - 7 edges
4. `register_builtins()` - 3 edges
5. `_not_found()` - 2 edges
6. `Cross-cloud edge dispatcher.  Picks a registered cloud by host suffix and proxie` - 1 edges
7. `WSGI app routing per-host to the matching cloud gateway.` - 1 edges
8. `Singleton registry of `CloudProvider` instances.` - 1 edges
9. `Multi-cloud meta-registry for LocalStack.  Each cloud lives under `localstack-co` - 1 edges
10. `Built-in cloud registrations. Imported lazily on first registry access.` - 1 edges

## Surprising Connections (you probably didn't know these)
- `MultiCloudEdge` --uses--> `CloudProvider`  [INFERRED]
  edge.py → base.py
- `MultiCloudEdge` --uses--> `CloudRegistry`  [INFERRED]
  edge.py → registry.py
- `CloudRegistry` --uses--> `CloudProvider`  [INFERRED]
  registry.py → base.py
- `register_builtins()` --calls--> `CloudProvider`  [INFERRED]
  builtin.py → base.py

## Communities (7 total, 4 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.22
Nodes (5): CloudProvider, Meta-types shared by every cloud module under `localstack-core/localstack/<cloud, Metadata + lazy factories describing a registered cloud implementation., Register the cloud providers shipped in this repo.      Idempotent: safe to call, register_builtins()

### Community 2 - "Community 2"
Cohesion: 0.32
Nodes (4): MultiCloudEdge, _not_found(), Cross-cloud edge dispatcher.  Picks a registered cloud by host suffix and proxie, WSGI app routing per-host to the matching cloud gateway.

## Knowledge Gaps
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `CloudProvider` connect `Community 1` to `Community 2`, `Community 3`?**
  _High betweenness centrality (0.560) - this node is a cross-community bridge._
- **Why does `CloudRegistry` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`, `Community 5`?**
  _High betweenness centrality (0.480) - this node is a cross-community bridge._
- **Why does `register_builtins()` connect `Community 1` to `Community 0`?**
  _High betweenness centrality (0.371) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `CloudRegistry` (e.g. with `MultiCloudEdge` and `CloudProvider`) actually correct?**
  _`CloudRegistry` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `CloudProvider` (e.g. with `MultiCloudEdge` and `CloudRegistry`) actually correct?**
  _`CloudProvider` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `MultiCloudEdge` (e.g. with `CloudProvider` and `CloudRegistry`) actually correct?**
  _`MultiCloudEdge` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Cross-cloud edge dispatcher.  Picks a registered cloud by host suffix and proxie`, `WSGI app routing per-host to the matching cloud gateway.`, `Singleton registry of `CloudProvider` instances.` to the rest of the system?**
  _8 weakly-connected nodes found - possible documentation gaps or missing edges._