# File: cognition/action_system.py

from typing import Any, Dict, Union, List, Optional
from aeiva.action.plan import Plan
from aeiva.action.skill import Skill
from aeiva.action.task import Task
from aeiva.action.action import Action
from aeiva.tool.tool import Tool
import asyncio

import os
import json

class ActionSystem:
    """
    A concrete Action System responsible for translating Plans into executable Skills
    and managing the execution of Skills.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.state = {
            "current_skill": None,
            "execution_status": "Not Started",
        }
        self.tools = []
        self.skill = None

    def setup(self) -> None:
        if "tools" in self.config.keys():
            for tool_name in self.config["tools"]:
                self.tools.append(Tool.load_tool_schema(tool_name))
        print("ActionSystem setup complete.")

    def plan_to_skill(self, plan: Plan) -> Skill:
        actions = []

        for task in plan.steps:
            if isinstance(task, Task):
                action = Action(
                    name=task.name,
                    params=task.params,
                    id=task.id,
                    dependent_ids=task.dependent_ids,
                    type="Action",
                    description=task.description,
                    metadata=task.metadata
                )
                actions.append(action)
            elif isinstance(task, Plan):
                sub_skill = self.plan_to_skill(task)  # Recursively handle sub-plans
                actions.append(sub_skill)
            else:
                raise TypeError(f"Unexpected step type: {type(task)} in plan {plan.id}")

        if not actions:
            raise ValueError(f"The plan {plan.id} does not contain any valid actions or sub-plans.")

        return Skill(
            name=plan.name,
            steps=actions,
            id=plan.id,
            dependent_ids=plan.dependent_ids,
            type="Skill",
            description=plan.description,
            metadata=plan.metadata
        )

    async def execute(self, plan: Plan) -> None:
        self.state["execution_status"] = "Executing"
        
        try:
            self.skill = self.plan_to_skill(plan)            
            await self.skill.execute()            
            self.state["execution_status"] = "Completed" if self.skill.is_successful else "Failed"
        except Exception as e:
            self.state["execution_status"] = "Failed"
            self.handle_error(e)
            raise  # Ensure to re-throw the exception

    def handle_error(self, error: Exception) -> None:
        print(f"ActionSystem encountered an error: {error}")