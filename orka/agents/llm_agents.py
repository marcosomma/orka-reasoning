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

import os
from openai import OpenAI
from dotenv import load_dotenv
from .agent_base import BaseAgent

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("BASE_OPENAI_MODEL", "gpt-3.5-turbo")

if not OPENAI_API_KEY:
    raise EnvironmentError("OPENAI_API_KEY environment variable is required")

client = OpenAI(api_key=OPENAI_API_KEY)

class OpenAIAnswerBuilder(BaseAgent):
    def run(self, input_data):
        full_prompt = f"{self.prompt}\n\n{input_data}"
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0
        )
        answer = response.choices[0].message.content.strip()
        return answer 

class OpenAIBinaryAgent(BaseAgent):
    def run(self, input_data):
        full_prompt = f"""
            {self.prompt}\n\n{input_data}. 
            ###Constrains: 
            - Answer strictly TRUE or FALSE.
        """
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer in ["true", "yes", "1"]

class OpenAIClassificationAgent(BaseAgent):
    def run(self, input_data):
        options = self.params.get("options", [])
        full_prompt = f"""{self.prompt}\n\n{input_data} 
            ###Constrains: 
            - Answer ONLY with one word.
            - Answer ONLY with one of the options.
            - Only pick from those options [{options}].
        """
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer if answer in options else "unknown"
