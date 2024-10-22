import asyncio
from aeiva.action.step import Step
from aeiva.action.procedure import Procedure
from aeiva.action.plan import Plan
from aeiva.action.skill import Skill
from aeiva.action.task import Task
from aeiva.action.experience import Experience
from aeiva.action.action import Action
from aeiva.action.action_system import ActionSystem
from aeiva.action.status import Status


# Test Step class
def test_step():
    print("\n--- Test Step ---")
    step = Step(name="TestStep", params={"param_1": "value_1"}, id="step_1", description="A test step")
    print("Step created:", step.to_dict())
    step.start()
    print("Step after start:", step.to_dict())
    step.end(success=True)
    print("Step after end (success):", step.to_dict())
    step.reset()
    print("Step after reset:", step.to_dict())


# Test Procedure class
def test_procedure():
    print("\n--- Test Procedure ---")
    step_1 = Step(name="Step1", params={"param_1": "value_1"}, id="step_1")
    step_2 = Step(name="Step2", params={"param_2": "value_2"}, id="step_2", dependent_ids=["step_1"])
    procedure = Procedure(name="TestProcedure", steps=[step_1, step_2], id="procedure_1")
    
    print("Procedure created:", procedure.to_dict())
    procedure.start()
    print("Procedure after start:", procedure.to_dict())
    procedure.end(success=True)
    print("Procedure after end:", procedure.to_dict())
    procedure.visualize()


# Test Plan class
def test_plan():
    print("\n--- Test Plan ---")
    task_1 = Step(name="Task1", params={"task_param": "value_1"}, id="task_1")
    task_2 = Step(name="Task2", params={"task_param": "value_2"}, id="task_2", dependent_ids=["task_1"])
    plan = Plan(name="TestPlan", steps=[task_1, task_2], id="plan_1", description="A test plan")
    
    print("Plan created:", plan.to_dict())
    plan.start()
    print("Plan after start:", plan.to_dict())
    plan.end(success=True)
    print("Plan after end:", plan.to_dict())
    plan.visualize()


# Test Skill class
async def test_skill():
    print("\n--- Test Skill ---")
    action_1 = Action(name="add", params={"a": 1, "b": 2}, id="add_action")
    action_2 = Action(name="test_operation", params={"a": 1, "b": 2}, id="test_operation_action", dependent_ids=["add_action"])
    action_3 = Action(name="fun_facts", params={}, id="fun_facts_action", dependent_ids=["add_action", "test_operation_action"])
    
    skill = Skill(name="TestSkill", steps=[action_1, action_2, action_3], id="skill_1")
    print("Skill created:", skill.to_dict())
    
    await skill.execute()
    print("Skill after execution:", skill.to_dict())
    skill.visualize()


# Test Experience class
def test_experience():
    print("\n--- Test Experience ---")
    action_1 = Action(name="add", params={"a": 1, "b": 2}, id="add_action")
    experience = Experience(name="TestExperience", steps=[action_1], owner="TestOwner")
    
    print("Experience created:", experience.to_dict())
    experience.mark_reliable()
    print("Experience marked reliable:", experience.to_dict())
    
    skill = experience.to_skill()
    print("Converted to Skill:", skill.to_dict())


# Test ActionSystem class
async def test_action_system():
    print("\n--- Test ActionSystem ---")
    
    # Create a Task and a Plan
    task_1 = Task(name="add", params={"a": 1, "b": 2}, id="add_task")
    task_2 = Task(name="test_operation", params={"a": 1, "b": 2}, id="test_operation_task", dependent_ids=["add_task"])
    plan = Plan(name="TestPlan", steps=[task_1, task_2], id="plan_1", description="A test plan")
    
    # Initialize Action System
    action_system = ActionSystem(config={})
    
    # Set up Action System
    await action_system.setup()
    
    # Execute the Plan
    await action_system.execute(plan)
    
    # Print the current Skill state after execution
    skill = action_system.get_current_skill()
    print("Current skill after execution:", skill.to_dict())


# Main function to run all tests
async def main():
    test_step()
    test_procedure()
    test_plan()
    await test_skill()
    test_experience()
    await test_action_system()

if __name__ == "__main__":
    asyncio.run(main())