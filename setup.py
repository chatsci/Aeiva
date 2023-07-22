from setuptools import setup, find_packages

setup(
    name='aeiva',
    version='0.1.0',
    license="Apache 2.0",
    author="Bang Liu",
    author_email="chatsci.ai@gmail.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
