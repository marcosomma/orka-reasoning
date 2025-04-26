# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka
#
# Licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://creativecommons.org/licenses/by-nc/4.0/legalcode
# For commercial use, contact: marcosomma.work@gmail.com
# 
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka

import abc

class BaseNode(abc.ABC):
    def __init__(self, node_id, prompt, queue, **kwargs):
        self.node_id = node_id
        self.prompt = prompt
        self.queue = queue
        self.params = kwargs
        self.type = self.__class__.__name__.lower()
        if(self.type == "failing"):
            self.agent_id = self.node_id

    @abc.abstractmethod
    def run(self, input_data):
        '''Run the logical node.'''
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} queue={self.queue}>"