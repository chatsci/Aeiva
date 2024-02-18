# Roadmap

**Author:** Bang Liu

**Date:** 2023-07-08

In this document, we describe the long- and short-term objectives of this project, as well as show the current plan in achieving the objectives.

## Long-term Objectives
Enable Aeiva to learn from multimodal and embodied environments with high learning efficiency and low-resource requirements. Specifically, we aim to research on the following aspects: (**Note:** the following may be updated based on recent research advances.)

**Input Data and Environment:**

* Multimodal learning
	* Be able to learn from video data, which is the main modality for human beings.
	* Be able to intergrate different modalities, e.g., text, image, audio, video, documents, and so on.

* Embodied learning
	* Be able to learn from embodied environments, e.g., MineDojo or any other video games, without reading internal states (i.e., by just observing raw visual inputs).
	* Be able to imagine the environment of videos and learn from them.
	* Unify the learning paradigm in different environments and different modalities.

**Output Data and Actions:**

* Manipulating tools
	* Enable the models to utilize tools, quickly learn new tools, and interact with different environments with tools

* Multimodal outputs
	* Enable the models to generate multimodal outputs, e.g., text, images, audios, videos.

**Model Architectures:**

* Small-scale model
	* Explore the ability limitations of small-scale models
	* Explore model architectures other than NN. E.g., SNN, more complex single neuron designs, neural science-inspired designs.
	* Achieving brain-scale model with high energy efficiency.
	
**Training Algorithms:**

* Efficient learning
	* Understand how LLMs learn with large-scale data
	* Improve the learning efficiency of language models.
	* The final goal is approaching or even surpassing the learning and energy efficiency of human brain.

**Better Understanding and Controlling AI:**

* Artificial Neural Science
	* Understand LLMs and other DL models: what they learned, how they learn, and how to improve.
	* Intergrating neural science knowledge to improve DL models.

* Safe, Controllable, Interpretable AI
	* Research on techniques to ensure safe, controllable, and interpretable AI

**AI Society**

* AI Society
	* Evolving a society of AI agents
	* Combining AI agents with virtual environment
	* Agents learn to solve problems in real-world
	* Ensure the human rights

**Applications:**

* AI for Science
	* Health
	* Material Science

The above research objectives are quite ambitious. However, we believe that it would be beneficial if we can develop a comprehensive framework that encompasses all these research objectives. Different researchers can focus on different parts/components. We aim to propose a general framework where each part can be easily replaced and tested. To achieve these, we aim to design a unified yet flexible framework to combine different parts.

## Short-term objectives (keep updating)
The long-term objective of this project is quite ambitious. At the first place, we want to better understand how the current LLMs learn, and improve the multimodal and embodied learning. Specifically, we want to learn from videos efficiently. Below is a list of milestones we aim to achieve in a short-term (keep updating): (**Note:** the following may be updated based on recent progress.)


* Multimodal Learning
	* Benchmarking several existing multimodal LLMs in a unified manner
	* Making model construction as easy as playing LEGO
	* Unifing different datasets
	* Define the general framework of multimodal learning
* Embodied Learning
	* Integrating several embodied environments, e.g., MineDojo, Alfred, etc.
	* Completing the framework of embodied learning, i.e., equiping LLMs with environments, actions, rewards, goals, and so on.
* AI Agent
	* Design agent and related classes
	* Design memory module
	* Design world model module
	* Design actions, rewards, etc.
	* Implement several learning algorithms.
* AI Society
	* Design AI community and communication protocals
	* Add visualizatioin UI

More ...

## Recent TODO list

Done? | Task <!--⬜️ Nope, ✅ Yep-->
:---:| ---
⬜️| Improve data item operators. Seperate util functions, specific operators, and common operators.
⬜️| Improve src/aeiva/common/types.py
⬜️| Support language model finetuning. Refer to NanoGPT.
⬜️| Incorporate different benchmarks and datasets: we need to easily evaluate different benchmarks to show the comparisions between different models or methods.
⬜️| Design model framework: how to integrate memory module, world model, etc.
⬜️| Design LEGO style protocal to construct models: how to easily extend or revise model.
⬜️| Design message protocal: how to percept different signals, how to output actions/different modalities. Use typed dict?
⬜️| Test on GPU environments.

