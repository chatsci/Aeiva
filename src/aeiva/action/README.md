
# README

Author: Bang Liu

Date: 2024-10-22

## Introduction

This framework introduces a well-structured system that organizes and manages different concepts like `Function`, `API`, `Tool`, `Action`, `Skill`, `Experience`, `Task`, `Plan`, `Step`, and `Procedure`. The system is designed to reflect a variety of tasks and executions, distinguishing between things that can be *executed* and things that can be *visualized*. Each concept is structured hierarchically and has a specific purpose, with clear relationships defined between them.

### Overview of Concepts

### 1. **Function**
A `Function` represents a clearly defined computational process or operation. It is fully transparent, with its internal implementation details revealed. A function takes input, processes it, and returns a result.

### 2. **API**
An `API` (Application Programming Interface) wraps a `Function` into an interface. It only reveals the function’s signature (e.g., name, parameters) while hiding the internal computation. APIs are often used to expose functionality to external services.

### 3. **Tool**
A `Tool` is an interface that can connect and utilize an `API`. Unlike an API, which is just an interface, a tool requires a connector (like an API server or a connecting function that can call it) to be utilized, and it allows interaction with external services or local functions.

### 4. **Action**
An `Action` is a `Tool` with states and state management methods. It inherits from `Step` and can be **executed**. Unlike `Task`, which is visual, an `Action` represents an executable process tied to a `Tool`. Actions are part of the broader system, where they manage execution states like `Not Executed`, `Executing`, `Success`, and `Fail`.

### 5. **Skill**
A `Skill` is a structured composition of `Actions`. Like `Action`, a `Skill` has states, state management, and can be **executed**. It inherits from `Procedure` and is designed to organize and manage a sequence of `Actions`. 

### 6. **Experience**
An `Experience` is similar to a `Skill`, but it is not yet validated for execution. It is a composition of `Actions`, but unlike `Skill`, it is **personalized**. It has an owner and an attribute indicating whether it is reliable enough to be transformed into a `Skill`. Experiences cannot be executed until they are marked reliable and transformed into a skill.

### 7. **Task**
A `Task` corresponds to an `Action`. It inherits from `Step` and is atomic, meaning it represents a single unit of work. Unlike an `Action`, a `Task` can be **visualized**, but not executed. It is mainly used for planning or organizing tasks, and it cannot manage states in terms of execution.

### 8. **Plan**
A `Plan` corresponds to a `Skill`. It inherits from `Procedure` and is a structured composition of `Tasks`. Unlike `Skill`, which deals with actions, a `Plan` is composed of tasks and is **visualized**, not executed. A plan represents a roadmap to achieving a goal through a series of organized tasks.



## Wrapping Relationships

### Function → API → Tool → Action → Skill

1. **Function**: The basic unit of computation.
2. **API**: Wraps a `Function` and exposes it as an interface, hiding its internal details.
3. **Tool**: Utilizes an API and connects it via a connector, allowing external interaction.
4. **Action**: A tool with state management, capable of being executed.
5. **Skill**: A composition of `Actions` that can be executed in sequence, respecting dependencies.



## Comparison Relationships

### Action vs Task
- **Action**: Tied to execution; inherits from `Step` and can execute functionality.
- **Task**: Atomic and visual; also inherits from `Step`, but is non-executable. It serves more for planning and organizing.

### Plan vs Skill vs Experience
- **Plan**: A roadmap for achieving a goal; composed of `Tasks` and **visualized**, not executed.
- **Skill**: A composition of `Actions` that can be **executed**, handling execution flow and dependencies.
- **Experience**: A composition of `Actions`, but it cannot be executed. It must first be validated and transformed into a `Skill`.


## Inheritance Relationships

### Action/Task and Step
Both `Action` and `Task` inherit from the base class `Step`. This means that both of them share common attributes like `id`, `description`, `status`, and `dependent_ids`. The difference lies in their purpose:
- `Action` can be executed.
- `Task` is used for visualization and planning.

### Plan/Skill/Experience and Procedure
`Plan`, `Skill`, and `Experience` all inherit from the `Procedure` base class. They share a structure that organizes steps (tasks, actions, sub-plans) in a directed acyclic graph (DAG). This structure ensures that steps follow dependencies and can be managed accordingly. 
- `Plan`: Visualizes `Tasks`.
- `Skill`: Executes `Actions`.
- `Experience`: Composes `Actions`, but cannot be executed until validated.



## Compositional Relationships

### Action and Skill
A `Skill` is composed of multiple `Actions`. The actions are organized and managed within the skill, which can execute them in the correct order based on their dependencies.

### Action and Experience
An `Experience` is also composed of multiple `Actions`, but these actions cannot be executed until the experience is validated.

### Task and Plan
A `Plan` is composed of multiple `Tasks`. The tasks within the plan are structured with dependencies, allowing the plan to visualize the flow of work required to achieve a goal.



## Visualization

                +------------------+          
                |      Function     |         
                +------------------+          
                           |               
                           v              
                +------------------+          
                |       API         |          
                +------------------+          
                           |               
                           v              
                +------------------+          
                |       Tool        |          
                +------------------+          
                           |               
                           v              
                +------------------+          
                |      Action       | (Inherits from Step)    
                +------------------+          
                           |               
                           v              
                +------------------+          
                |      Skill        | (Inherits from Procedure, composed of Actions) 
                +------------------+          
                           ^               
                           | Transform              
                +------------------+          
                |   Experience      | (Inherits from Procedure, composed of Actions) 
                +------------------+                  
	  
			      +------------------+
			      |     Task         |
			      +------------------+
			                | Inherits from           
			                v Step                     

				+------------------+
				|     Plan         |
				| (composed of     |
				| Tasks, visualized| 
				| not executed)    |
				+------------------+
							| Inherits from
							v Procedure


Summary:
- **Function -> API -> Tool -> Action**: Wrapping relationship from Function to Action.
- **Action vs. Task**: Both inherit from Step. Action is executable with tools, while Task is visualized.
- **Skill vs. Plan**: Both inherit from Procedure. Skill is composed of Actions (executed), Plan is composed of Tasks (visualized).
- **Experience**: Like Skill but not executable until validated (personalized ownership).


## Action System

The **Action System** bridges cognitive outputs (Plans) to executable actions (Skills). It transforms high-level Plans into structured Skills, which consist of Actions tied to specific Tools for execution. 

### Design Philosophy:

1. **Separation of Cognition and Execution**:
    - The Action System handles **execution** only, keeping cognitive reasoning (e.g., Plan creation) separate from actionable processes.

2. **Plan-to-Skill Transformation**:
    - **Plans** are mapped to **Skills**, where each Task in a Plan is translated into an **Action**, and each Action is connected to a **Tool** that executes the operation (API, function, etc.).

3. **Tool Integration**:
    - Actions in the system are powered by Tools, which wrap APIs and other executable functions, allowing flexible integration with external services.

4. **Execution Management**:
    - Skills are executed asynchronously, and the Action System manages their state, tracking success, failure, and in-progress statuses for each Action.

5. **Recursive Structure**:
    - Supports nested Plans and Skills, enabling hierarchical workflows for complex task execution.

### Example Workflow:

1. **Cognitive System**: An LLM generates a **Plan**.
2. **Plan-to-Skill**: The Action System converts the Plan into a **Skill**.
3. **Execution**: The Skill is executed, with each Action utilizing a **Tool**.
4. **Status Feedback**: The system tracks and reports the execution status of each Action.

The Action System ensures modular, scalable, and flexible execution by separating reasoning from action and supporting complex workflows through recursive task decomposition.

## Conclusion

This framework defines a clear hierarchy and structure for managing tasks, actions, skills, and experiences. With proper execution management and planning, it allows for complex workflows to be handled efficiently, ensuring that tasks are visualized and actions are executed in the correct order.


