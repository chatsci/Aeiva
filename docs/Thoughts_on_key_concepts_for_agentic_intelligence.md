
# Thoughts on Several Key Concepts for Agentic Intelligence

**Author:** Bang Liu

**Date:** 2023-10-21

In building an intelligent agent system, especially one designed to perform complex tasks and learn from experience, it is crucial to clearly define core concepts that guide its behavior. These concepts shape how the agent interacts with its environment, executes tasks, learns from past experiences, and acquires new knowledge. Below are my thoughts on several key concepts, enriched with examples to make them more tangible.

---

## 1. What is a Plan?

A **Plan** is a structured, goal-driven roadmap for an agent to achieve a specific task. The key feature of a Plan is that it decomposes the primary task into subtasks, forming a hierarchical structure. The agent follows this roadmap, completing one subtask after another. Since a plan ultimately governs execution, it must be well-structured—most naturally as a Directed Acyclic Graph (DAG). 

Each node in the DAG represents a **Task** or subtask, and the edges describe dependencies between them. This ensures a logical, stepwise execution where subtasks cannot begin until their dependencies are satisfied.

- **Example**: Consider an agent tasked with preparing a meal. The plan breaks the main task ("Cook meal") into subtasks like "Chop vegetables," "Boil water," "Cook rice," and "Serve meal." Some tasks must precede others (e.g., "Boil water" must happen before "Cook rice"). This structure forms a DAG, ensuring tasks are completed in the correct order without cycles or deadlocks.

---

## 2. What is a Task?

A **Task** is the fundamental unit of work in a plan. Each task has a clear **status**, which can be one of:
- **Not Executed**: The task is yet to be started.
- **Executing**: The task is currently being performed.
- **Success**: The task has been completed successfully.
- **Fail**: The task has failed, possibly requiring intervention or retry.

Tasks can have **meta-data** such as the task owner, creation time, priority, or other relevant attributes. A task also needs a mechanism to check whether it has been completed successfully, which might involve running tests or checking outputs against expectations.

- **Example**: In a factory, an agent may have a task like "Assemble component A." The task could have metadata such as who is responsible (agent A or robot arm B), creation time (timestamp when this task was queued), and a priority level (perhaps "high" because component A is needed soon). After execution, the task might check the assembled part for defects before marking itself as "Success."

---

## 3. What is a Tool?

A **Tool** provides functionality that the agent can use to perform actions. In modern software, a tool often takes the form of an **API**—a set of operations that accept inputs (parameters) and return outputs (results). 

Tools can be seen as atomic units of functionality that are executed in isolation, but their results can influence the broader task or plan. Tools are often reusable across different tasks or plans.

- **Example**: Consider a research assistant agent that interacts with a remote API to retrieve scientific papers. Here, the "Arxiv API" is a tool. The agent calls this API (providing search parameters), and the tool returns a list of papers in a structured format. The agent uses this tool to complete tasks like "Find papers related to quantum computing."

---

## 4. What is an Action?

An **Action** is a higher-level operation the agent can take. While it may **use a tool** (or multiple tools), it is broader than just invoking a function. An Action might involve decision-making, performing logic internally, or combining the output of multiple tools. 

Whereas tools are about "doing one thing well," actions are more about **how** the agent decides to use tools or perform processes. Some actions may not even require external tools but might involve manipulating data internally.

- **Example**: A warehouse robot's action could be "Pick up an item from shelf A and place it in bin B." The action uses the robot’s sensors and movement tools, but the decision-making on how to execute it—like which arm to use or which path to follow—is part of the action.

---

## 5. What is a Skill?

A **Skill** is the procedural knowledge an agent uses to complete a task. It represents a series of actions or steps the agent follows to solve a problem. Skills can be encoded as DAGs, with each node representing an action, and the edges defining the flow or dependencies between actions.

What distinguishes a **Skill** from hardcoded instructions is its **flexibility**. For instance, a skill may allow for different actions to be taken in varying orders, or certain parameters may be adjusted dynamically. In other words, a skill isn’t rigid but adaptable to different contexts or environments.

- **Example**: An agent trained to clean a room could have a "Cleaning skill." It involves subtasks like "vacuum the floor," "wipe the table," and "empty the trash." In some cases, the agent may vacuum first and then wipe the table, but in others, it may reverse the order depending on room conditions. The ability to adapt while following a general cleaning procedure is what makes it a skill.

---

## 6. What is an Experience?

An **Experience** is a personal record of how an agent solved a particular task. While the structure of an **Experience** may resemble that of a **Skill**, it is tied to a specific instance. 

The main distinction is that **Experiences are not generalized**. Instead, they capture the details of how a task was solved under particular circumstances, including all the decisions, parameters, and actions taken during the process. Over time, multiple experiences can be analyzed to derive common patterns, which evolve into **Skills**.

- **Example**: After attempting to solve several puzzles, an agent might log each experience—how it solved the puzzle, what tools it used, how long it took, etc. After analyzing several such experiences, the agent may extract a general strategy (skill) for solving puzzles of this type.

---

## 7. What is Memory?

**Memory** is the broader concept that includes all the data an agent remembers about its past actions, interactions, and decisions. Memory could encompass many forms, including:
- **Experiential memory**: Specific memories about how the agent solved tasks (as described in Experience).
- **Episodic memory**: Memory of specific events or interactions the agent has been part of.
- **Semantic memory**: Knowledge the agent has learned about its environment or domain.

Memory plays a critical role in making an agent "intelligent," as it allows the agent to learn from past mistakes, reuse successful strategies, and adapt to new situations by recalling prior experiences.

- **Example**: A personal assistant agent might have episodic memory of the last time it scheduled a meeting for the user. The next time the user asks it to schedule a meeting, it can reference that memory to understand the user's preferences, such as their preferred meeting time.

---

## 8. What is Knowledge?

**Knowledge** is a validated, generalizable form of learning. While an experience is a personal, one-off record, knowledge has been abstracted and validated across multiple situations. Knowledge allows the agent to **generalize** beyond specific experiences and apply what it has learned to new, similar tasks.

In many cases, a **Skill** represents a particular type of knowledge—the procedural knowledge required to complete a task. Knowledge might also be sharable between agents, or taught from one agent to another, making it reusable.

- **Example**: An agent that has learned to solve various types of math problems can generalize its knowledge into a set of skills. When faced with a new math problem, it can apply this knowledge, even if the problem differs slightly from the ones it has solved before.

---

## Closing Thoughts

These key concepts—**Plan, Task, Tool, Action, Skill, Experience, Memory, and Knowledge**—form the foundation of agentic intelligence. Together, they allow an agent to:
- Decompose tasks into executable steps (Plan),
- Perform specific actions (Task, Action, Tool),
- Learn from both immediate tasks and general experiences (Experience, Memory),
- Generalize that learning into knowledge that improves future performance (Knowledge, Skill).

By keeping these concepts clear and well-defined, an agent can operate in a structured, intelligent way, continually learning and improving over time.
