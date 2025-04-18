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

class BaseAgent(abc.ABC):
    def __init__(self, agent_id, prompt, queue, **kwargs):
        self.agent_id = agent_id
        self.prompt = prompt
        self.queue = queue
        self.params = kwargs
        self.type = self.__class__.__name__.lower()  

    @abc.abstractmethod
    def run(self, input_data):
        '''Run the agent's reasoning process.'''
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} id={self.agent_id} queue={self.queue}>"