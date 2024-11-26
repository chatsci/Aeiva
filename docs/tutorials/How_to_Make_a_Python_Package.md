
# How to Make Your Python Project a Pip-Installable Package

Author: Bang Liu

Date: 2024-11-23

This guide walks you through the process of creating a Python package that others can install using `pip`.

---

## Step 1: Structure Your Project

Organize your project with a proper directory structure:

```
your_project/
├── src/
│   └── your_project/
│       ├── __init__.py  # Makes this a package
│       ├── module.py    # Your module files
├── setup.py             # Metadata and build script
├── README.md            # Project description
├── LICENSE              # License file (optional but recommended)
├── requirements.txt     # Dependency file (optional)
```

- **`src/your_project/`**: Contains your package code.
- **`__init__.py`**: Makes the folder a Python package.
- **`setup.py`**: Defines metadata and installation behavior.

---

## Step 2: Create `setup.py`

`setup.py` is the script used to build and install your package. Here's a sample:

```python
from setuptools import setup, find_packages

setup(
    name="your_project",                # Your package name
    version="0.1.0",                    # Package version
    author="Your Name",                 # Your name
    author_email="your.email@example.com",  # Your email
    description="A brief description",  # Short description
    long_description=open('README.md').read(),  # Long description from README
    long_description_content_type='text/markdown',  # Markdown format
    url="https://github.com/username/repository",  # Project repository
    packages=find_packages(where="src"),           # Find packages in src/
    package_dir={"": "src"},            # Root directory for packages
    classifiers=[                       # Metadata for PyPI
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',            # Minimum Python version
    install_requires=[                  # Dependencies
        "numpy",  # Example dependency
    ],
)
```

---

## Step 3: Create `README.md`

Write a `README.md` file to describe your project. Use Markdown for formatting. Example:

```markdown
# Your Project Name

A short description of your project.

## Installation

```bash
pip install your_project
```

## Usage

```python
import your_project
your_project.some_function()
```


---

## Step 4: Test Your Package Locally

Test your package before publishing:

1. Navigate to your project root:
   ```bash
   cd /path/to/your_project
   ```

2. Install it in editable mode:
   ```bash
   pip install -e .
   ```

3. Import your package to verify:
   ```bash
   python
   >>> import your_project
   >>> your_project.some_function()
   ```

---

## Step 5: Build the Package

Install the necessary tools:

```bash
pip install build
```

Build your package:

```bash
python -m build
```

This creates a `dist/` directory with `.tar.gz` and `.whl` files.

---

## Step 6: Upload to PyPI

1. **Register on PyPI**:
   - Create an account at [PyPI](https://pypi.org/).
   - Optionally, register on [TestPyPI](https://test.pypi.org/) for testing.

2. **Install Twine**:
   ```bash
   pip install twine
   ```

3. **Upload Your Package**:
   ```bash
   python -m twine upload dist/*
   ```

   To test uploads on TestPyPI:
   ```bash
   python -m twine upload --repository testpypi dist/*
   ```

4. **Provide Your PyPI Token**:
   - If prompted, enter your PyPI API token.

5. Alternate way to uplaod
```bash
python -m twine upload --repository-url https://upload.pypi.org/legacy/ dist/* -u __token__ -p pypi-<your token password here>
```

---

## Step 7: Verify Installation

Install your package from PyPI:

```bash
pip install your_project
```

Verify it works as expected:

```python
python
>>> import your_project
>>> your_project.some_function()
```

---

## Tips and Best Practices

- **Include a License**: Add a `LICENSE` file to clarify usage terms.
- **Automate Versioning**: Use tools like `bumpversion` to manage versions.
- **Test Thoroughly**: Use TestPyPI before uploading to the main PyPI repository.
- **Secure Tokens**: Use project-specific tokens for uploads.

---

Congratulations! Your project is now a pip-installable Python package.
