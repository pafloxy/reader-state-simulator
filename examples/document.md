We want to find every vertex reachable from a chosen start vertex by following directed edges.

Keep a collection called pending of vertices waiting to be explored. Initially it contains the start vertex.

We also keep a set called seen, initially containing the start vertex.

When we explore a vertex, inspect each of its outgoing neighbors and consider whether to schedule that neighbor.

Schedule a neighbor only if it is absent from seen, and add it to seen immediately when scheduling it. Thus no vertex is scheduled twice, even when the graph has a cycle.