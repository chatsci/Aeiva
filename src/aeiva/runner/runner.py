from typing import Callable, Dict, List, Optional, Any


class OperatorNode:
    def __init__(self, name: str, func: Callable, input_links: Optional[List[str]] = None, condition=None):
        self.name = name
        self.func = func
        self.input_links = input_links if input_links is not None else []
        self.output_links = []
        self.status = 'idle'
        self.outputs = None
        self.condition = condition

    def execute(self, inputs: dict):
        if self.status != 'idle':
            raise RuntimeError(f"Operator {self.name} is not in 'idle' state. Current state: {self.status}")

        if self.condition is None or self.condition():
            print(f"Running operator {self.name}")
            self.status = "running"
            self.outputs = self.func(inputs)
            self.status = 'completed'
            return self.outputs
        else:
            print(f"Skipping execution of {self.name} due to unmet condition.")
            self.status = "skipped"
            return None

    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        return self.execute(inputs)


class ComputationGraph:
    def __init__(self):
        self.operator_nodes = {}
        self.execution_order = None
        self.context = {}  

    def add_operator(self, operator_node):
        self.operator_nodes[operator_node.name] = operator_node
        self.execution_order = None  # Reset the execution order

    def build(self):
        visited = set()
        self.execution_order = []

        def visit(op_name):
            if op_name not in visited:
                visited.add(op_name)
                if op_name in self.operator_nodes:
                    for dep in self.operator_nodes[op_name].input_links:
                        visit(dep)
                    self.execution_order.append(op_name)

        for op_name in self.operator_nodes:
            visit(op_name)
    
    def reset(self):
        for operator in self.operator_nodes.values():
            operator.status = 'idle'
            operator.outputs = None
        self.execution_order = None
        self.context = {}
 
    def run(self, inputs):
        self.context = inputs
        if self.execution_order is None:
            self.build()
        for op_name in self.execution_order:
            operator = self.operator_nodes[op_name]
            result = operator.execute(self.context)
            if result is not None:
                self.context.update(result)

    def __call__(self, inputs: Dict[str, Any]):
        self.reset()
        self.run(inputs)
        return self.context


class Runner:
    def __init__(self):
        self.graph = ComputationGraph()
        self.operators = {}
        self.dirty = False

    def add_operator(self, name: str, function: Callable):
        node = OperatorNode(name, function)
        self.graph.add_operator(node)
        return node

    def link_operators(self, source: OperatorNode, target: OperatorNode):
        target.input_links.append(source)

    def stack_operators(self, operators: List[OperatorNode]):
        for i in range(1, len(operators)):
            self.link_operators(operators[i-1], operators[i])

    def build_graph(self):
        if self.dirty:  
            for name, operator in self.operators.items():
                self.graph.add_operator(operator)
            self.graph.build()
            self.dirty = False
    
    def reset(self):
        self.graph.reset()

    def clear(self):
        self.graph = ComputationGraph()
        self.operators = {}
        self.dirty = False

    def run(self, inputs: Dict[str, Any]):
        self.build_graph()
        self.graph.run(inputs)

    def __call__(self, inputs: Dict[str, Any]):
        self.build_graph()
        return self.graph(inputs)
