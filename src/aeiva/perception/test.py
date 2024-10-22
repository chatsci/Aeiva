from aeiva.perception.sensation import Signal
from aeiva.perception.stimuli import Stimuli
from datetime import datetime


def test_signal():
    print("Testing Signal class...")

    # Create the first signal
    signal1 = Signal(
        data="Image data",
        modularity="image",
        type="image",
        timestamp="2024-10-23T12:00:00Z"
    )
    print(f"Signal 1: {signal1.to_dict()}")

    # Create the second signal, depending on the first signal using dependencies
    dependencies = {"s2": {"s1": {}}}  # s2 depends on s1
    signal2 = Signal(
        data="Text data",
        modularity="text",
        type="document",
        id="s2",
        metadata={"language": "en"},
        dependencies=dependencies  # Updated to use 'dependencies'
    )
    print(f"Signal 2: {signal2.to_dict()}")


def test_stimuli():
    print("Testing Stimuli class...")

    # Create two signals
    signal1 = Signal(
        data="Audio data",
        modularity="audio",
        type="speech",
        timestamp="2024-10-23T12:30:00Z",
        id="s1"
    )
    signal2 = Signal(
        data="Video data",
        modularity="video",
        type="video",
        timestamp="2024-10-23T12:45:00Z",
        id="s2"
    )

    # Create Stimuli with dependencies between signals
    dependencies = {
        "s2": {"s1": {}}  # signal2 (s2) depends on signal1 (s1)
    }

    stimuli = Stimuli(
        signals=[signal1, signal2],
        id="stimuli1",
        name="Test Stimuli",
        type="multimodal",
        timestamp="2024-10-23T13:00:00Z",
        dependencies=dependencies
    )

    print(f"Stimuli: {stimuli.to_dict()}")

    # Traverse the stimuli using DFS and BFS
    dfs_traversal = stimuli.traverse(method='dfs')
    print("DFS Traversal:")
    for node in dfs_traversal:
        print(f" - {node.id}: {node.type}")

    bfs_traversal = stimuli.traverse(method='bfs')
    print("BFS Traversal:")
    for node in bfs_traversal:
        print(f" - {node.id}: {node.type}")

    # Visualize the stimuli structure
    stimuli.visualize()


if __name__ == "__main__":
    test_signal()
    test_stimuli()