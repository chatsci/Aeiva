from setuptools import setup, find_packages

setup(
    name='aeiva',
    version='0.8.0',
    license="Apache 2.0",
    author="Bang Liu",
    author_email="chatsci.ai@gmail.com",
    description="AEIVA: An Evolving Intelligent Virtual Assistant",
    long_description=open('README.md').read(),  # Ensure the README.md exists and is correct
    long_description_content_type='text/markdown',  # Use 'text/markdown' for Markdown files
    url="https://github.com/chatsci/Aeiva",  # Replace with your actual repository URL
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.9',
)
