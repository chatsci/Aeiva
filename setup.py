from setuptools import setup, find_packages

setup(
    name='aeiva',
    version='0.8.1',
    license="Apache 2.0",
    author="Bang Liu",
    author_email="chatsci.ai@gmail.com",
    description="AEIVA: An Evolving Intelligent Virtual Assistant",
    long_description=open('README.md').read(),  # Ensure the README.md exists and is correct
    long_description_content_type='text/markdown',  # Use 'text/markdown' for Markdown files
    url="https://github.com/chatsci/Aeiva",  # Replace with your actual repository URL
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'aeiva-chat-terminal=aeiva.command.aeiva_chat_terminal:run',
            'aeiva-chat-gradio=aeiva.command.aeiva_chat_gradio:run',
            'aeiva-server=aeiva.command.aeiva_server:run',
            'maid-chat=aeiva.command.maid_chat:run',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)
