<p align="center" width="100%">
<img src="assets/aeiva-logo-Medusa.png" alt="AEIVA" style="width: 70%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# AEIVA: An Evolving Intelligent Virtual Assistant

<p align="center">
<a href="docs/README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<!-- <a href="docs/README_JA.md"><img src="https://img.shields.io/badge/ドキュメント-日本語-blue.svg" alt="JA doc"></a> -->
<!-- <a href="https://discord.gg/wCp6Q3fsAk"><img src="https://dcbadge.vercel.app/api/server/wCp6Q3fsAk?compact=true&style=flat" alt="Discord Follow"></a> -->
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
<!-- <a href="docs/ROADMAP.md"><img src="https://img.shields.io/badge/ROADMAP-路线图-blue" alt="roadmap"></a> -->
<!-- <a href="docs/resources/MetaGPT-WeChat-Personal.jpeg"><img src="https://img.shields.io/badge/WeChat-微信-blue" alt="roadmap"></a> -->
<!-- <a href="https://twitter.com/DeepWisdom2019"><img src="https://img.shields.io/twitter/follow/MetaGPT?style=social" alt="Twitter Follow"></a> -->
</p>


In this project, our objective is to develop a modular and flexible intelligent agent and society system, designed as a virtual assistant capable of performing diverse tasks, learning from data, environment, and interactions, and self-evolving over time. The system will leverage deep learning models, primarily transformers, while also exploring innovative models and learning methods. A key focus will be on enhancing model interpretability, safety, and conducting thorough analysis to advance research in these areas. Our big goal? To understand the essence of intelligence and use this knowledge to make life better for people.


## Installation
To install AEIVA, follow these steps:
### Prerequisites
* Python 3.9 or newer
* pip (Python package manager)

### Steps
1. **Clone the AEIVA Repository**

	First, clone the AEIVA repository to your local machine using Git:

	```bash
	git clone https://github.com/chatsci/Aeiva.git
	cd Aeiva
	```

2. **Create a Virtual Environment (Recommended)**
It's a good practice to create a virtual environment for Python projects. This keeps dependencies required by different projects separate. Use the following command to create a virtual environment with `conda`:

	```bash
	conda create --name <my-env>
	```
	
	Replace `<my-env>` with the name of your environment.
	
	To acivate your env:
	
	```bash
	conda activate <my-env>
	```
	
	For more advanced configurations or options, please check the online document of `conda`.
	
3. **Install Dependencies**
	Install all dependencies listed in **requirements.txt**:
	
	```bash
	pip install -r requirements.txt
	```

4. **Install Aeiva**
	Finally, install AEIVA using the **setup.py** script:
	
	```bash
	python setup.py install
	```
	
5. **Verify Installation**
	To verify that AEIVA has been installed correctly, you can run the following command:
	
	```bash
	python -c "import aeiva; print(aeiva.__version__)"
	```

## Demo

* **Multimodal chatbot**
	To run a multimodal chatbot, run the following command (assume you are in the project folder `Aeiva/`):
	
	```bash
	python src/aeiva/demo/mm_chatbot.py
	```
	Once the demo is running, go to the local URL address indicated in the terminal. You will see a Gradio interface like below:
	![mm_chatbot](assets/mm_chat_demo.png)	
	You may change your path if you are in a different folder.

**Note:** We will add more demos or examples.

## Contact
![contact](assets/contact.png)
## Acknowledge




