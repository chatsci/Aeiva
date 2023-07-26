from aeiva.runner.runner import Runner
import numpy as np


class LearnableRunner(Runner):
    def __init__(self, cfg, operators):
        super().__init__(cfg, operators)
        self.cfg = cfg
        self.operators = operators

    def optimize(self, reward_function, search_algorithm):
        best_reward = -np.inf
        best_graph = None

        for _ in range(self.cfg.optimization_steps):
            graph = search_algorithm.sample()
            self.run(graph)
            reward = reward_function()

            if reward > best_reward:
                best_reward = reward
                best_graph = graph

        return best_graph
