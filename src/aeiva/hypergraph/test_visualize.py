# aeiva/hypergraph/tests/test_visualization.py

import matplotlib.pyplot as plt
from aeiva.hypergraph.hypergraph import Hypergraph
from aeiva.hypergraph.visualization import draw_rubber_band, draw_two_column
from aeiva.hypergraph.exceptions import HypergraphError
import networkx as nx
import numpy as np
from collections import defaultdict
from typing import Any

def get_collapsed_size(v: Any) -> int:
    try:
        if isinstance(v, str) and ":" in v:
            return int(v.split(":")[-1])
    except:
        pass
    return 1

def main():
    # Example 1: Basic Visualization
    scenes = {
        0: {"nodes": ('FN', 'TH')},
        1: {"nodes": ('TH', 'JV')},
        2: {"nodes": ('BM', 'FN', 'JA')},
        3: {"nodes": ('JV', 'JU', 'CH', 'BM')},
        4: {"nodes": ('JU', 'CH', 'BR', 'CN', 'CC', 'JV', 'BM')},
        5: {"nodes": ('TH', 'GP')},
        6: {"nodes": ('GP', 'MP')},
        7: {"nodes": ('MA', 'GP')}
    }

    # Initialize node properties
    node_props = {}
    for he in scenes.values():
        for node in he["nodes"]:
            node_props[node] = {}

    # Initialize hyperedge properties
    hyperedge_props = {he_id: {} for he_id in scenes}

    H = Hypergraph(
        hyperedges=scenes,
        node_properties=node_props,
        hyperedge_properties=hyperedge_props,
        name="Les Miserables Scenes"
    )

    # Plot 1: Default Rubber Band Style
    plt.figure(figsize=(8, 8))
    draw_rubber_band(H)
    plt.title("Rubber Band Visualization")
    plt.show()

    # Plot 2: Dual Hypergraph Rubber Band Style
    plt.figure(figsize=(8, 8))
    draw_rubber_band(H.dual())
    plt.title("Dual Hypergraph Rubber Band Visualization")
    plt.show()

    # Plot 3: Collapsed Nodes with Counts
    # Assuming collapse_duplicate_nodes is implemented in Hypergraph
    try:
        H_collapsed = H.collapse_duplicate_nodes()
    except AttributeError:
        print("collapse_duplicate_nodes method not implemented in Hypergraph. Skipping collapsed nodes visualization.")
        H_collapsed = H

    plt.figure(figsize=(8, 8))
    draw_rubber_band(H_collapsed, with_node_counts=True)
    plt.title("Rubber Band Visualization with Collapsed Nodes")
    plt.show()

    # Plot 4: Two Column Layout
    plt.figure(figsize=(8, 8))
    draw_two_column(H)
    plt.title("Two Column Visualization")
    plt.show()

    # Example 2: Busy Hypergraph (Without pandas)
    # Define hyperedges with weights
    busy_scenes = {
        'Topic1': {'Node1', 'Node2', 'Node3'},
        'Topic2': {'Node2', 'Node4'},
        'Topic3': {'Node1', 'Node3', 'Node4', 'Node5'},
        'Topic4': {'Node3', 'Node5'},
        'Topic5': {'Node4', 'Node5'},
    }

    hyperedges_busy = {}
    node_properties_busy = defaultdict(dict)
    hyperedge_properties_busy = {}

    for he_id, nodes in busy_scenes.items():
        hyperedges_busy[he_id] = {'nodes': list(nodes), 'properties': {'weight': len(nodes)}}
        hyperedge_properties_busy[he_id] = {'weight': len(nodes)}
        for node in nodes:
            node_properties_busy[node] = {}

    H_busy = Hypergraph(
        hyperedges=hyperedges_busy,
        node_properties=node_properties_busy,
        hyperedge_properties=hyperedge_properties_busy,
        name="Busy Hypergraph"
    )

    # Define color mapping based on weights
    norm = plt.Normalize(vmin=min([props['weight'] for props in hyperedge_properties_busy.values()]),
                        vmax=max([props['weight'] for props in hyperedge_properties_busy.values()]))
    cmap = plt.cm.Greens

    def get_cell_color(e):
        weight = H_busy.hyperedge_properties.get(e, {}).get('weight', 0)
        return cmap(norm(weight))

    plt.figure(figsize=(12, 12))
    draw_rubber_band(
        H_busy,
        with_additional_edges=H_busy.to_bipartite_graph(),
        edges_kwargs={
            'edgecolors': 'darkgray',
            'facecolors': (.65, .65, .65, .15)
        },
        additional_edges_kwargs={
            'edge_color': [get_cell_color(e) for e in H_busy.hyperedges.keys()],
            'width': 4,
        },
        edge_labels_on_edge=False,
        contain_hyper_edges=True
    )
    plt.title("Busy Hypergraph Rubber Band Visualization")
    plt.show()

    # Subhypergraph focusing on the most interesting edges
    threshold = 2  # Example threshold based on weight

    # Filter out singletons and small weights
    filtered_hyperedges = {he_id: he for he_id, he in H_busy.hyperedges.items() if len(he.nodes) > 1 and he.properties['weight'] >= threshold}

    node_set = set()
    for he in filtered_hyperedges.values():
        node_set.update(he.nodes)

    hyperedges_filtered = {he_id: he.to_dict() for he_id, he in filtered_hyperedges.items() if he.nodes & node_set}

    node_properties_filtered = {node: {} for node in node_set}
    hyperedge_properties_filtered = {he_id: he["properties"] for he_id, he in hyperedges_filtered.items()}

    H2 = Hypergraph(
        hyperedges=hyperedges_filtered,
        node_properties=node_properties_filtered,
        hyperedge_properties=hyperedge_properties_filtered,
        name="Filtered Busy Hypergraph"
    )

    def get_cell_color_filtered(e):
        return cmap(norm(H2.hyperedge_properties.get(e, {}).get('weight', 0)))

    plt.figure(figsize=(12, 12))
    draw_rubber_band(
        H2,
        with_additional_edges=H2.to_bipartite_graph(),
        edges_kwargs={
            'edgecolors': 'darkgray',
            'facecolors': (.65, .65, .65, .15)
        },
        additional_edges_kwargs={
            'edge_color': [get_cell_color_filtered(e) for e in H2.hyperedges.keys()],
            'width': 4,
        },
        edge_labels_on_edge=False,
        contain_hyper_edges=True
    )
    plt.title("Filtered Busy Hypergraph Rubber Band Visualization")
    plt.show()


if __name__ == "__main__":
    main()