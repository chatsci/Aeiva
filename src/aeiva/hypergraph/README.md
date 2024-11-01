# AEIVA Hypergraph

![PyPI](https://img.shields.io/pypi/v/aeiva-hypergraph)
![License](https://img.shields.io/pypi/l/aeiva-hypergraph)
![Python Version](https://img.shields.io/pypi/pyversions/aeiva-hypergraph)

AEIVA Hypergraph is a Python library for creating, analyzing, and visualizing hypergraphs. It provides a comprehensive suite of tools to work with hypergraphs, including construction from various data formats, property management, connectivity analysis, and intuitive visualization capabilities.

## Features

- **Hypergraph Construction**: Create hypergraphs from dictionaries, pandas DataFrames, NumPy arrays, and bipartite NetworkX graphs.
- **Property Management**: Assign and manage properties to nodes, hyperedges, and incidences.
- **Analysis Tools**: Perform connectivity checks, calculate diameters, and more.
- **Visualization**: Visualize hypergraphs with customizable layouts and styling options.
- **Serialization**: Save and load hypergraphs to/from JSON and CSV formats.

## Installation

You can install AEIVA Hypergraph via pip:

```bash
pip install aeiva-hypergraph
```

You can install AEIVA Hypergraph via pip:

```bash
pip install aeiva-hypergraph
```

Alternatively, install from source:

```bash
git clone https://github.com/yourusername/aeiva-hypergraph.git
cd aeiva-hypergraph
pip install .
```

## Quick Start

### Creating a Hypergraph

```python
from aeiva.hypergraph.construction import HypergraphConstruction

# Create hypergraph from a dictionary
data_dict = {
    'E1': ['A', 'B'],
    'E2': ['B', 'C'],
    'E3': ['C', 'D']
}
H = HypergraphConstruction.from_dict(data_dict, name="MyHypergraph")
```

### Analyzing the Hypergraph

```python
from aeiva.hypergraph.analysis import ConnectivityAnalyzer, DiameterCalculator

# Check connectivity
analyzer = ConnectivityAnalyzer(H)
is_connected = analyzer.is_connected()
print(f"Is connected: {is_connected}")

# Calculate diameter
calculator = DiameterCalculator(H)
if is_connected:
    diameter = calculator.calculate_diameter()
    print(f"Diameter: {diameter}")
```

### Visualizing the Hypergraph

```python
import matplotlib.pyplot as plt
from aeiva.hypergraph.visualize import draw

fig, ax = plt.subplots()
draw(H, ax=ax, with_color=True, with_node_labels=True, with_edge_labels=True)
plt.show()
```

### Saving and Loading Hypergraphs

```python
from aeiva.hypergraph.io import HypergraphIO

# Save to JSON
HypergraphIO.write_to_json(H, "hypergraph.json")

# Load from JSON
loaded_H = HypergraphIO.read_from_json("hypergraph.json")
```

## Documentation

Comprehensive documentation is available here.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

	1.	Fork the repository
	2.	Create your feature branch (git checkout -b feature/YourFeature)
	3.	Commit your changes (git commit -m 'Add some feature')
	4.	Push to the branch (git push origin feature/YourFeature)
	5.	Open a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

	•	NetworkX
	•	Matplotlib
	•	NumPy
	•	Pandas
	•	SciPy


## Folder Structure
aeiva/
└── hypergraph/
    ├── __init__.py
    ├── analysis.py
    ├── construction.py
    ├── exceptions.py
    ├── hyperedge.py
    ├── hypergraph.py
    ├── io.py
    ├── properties.py
    ├── utils.py
    └── visualize.py

tests/
├── __init__.py
├── test_analysis.py
├── test_construction.py
├── test_hyperedge.py
├── test_hypergraph.py
├── test_io.py
├── test_intersection.py
├── test_union.py
├── test_utils.py
└── test_visualize.py

setup.py
requirements.txt
README.md