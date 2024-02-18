# How to generate docs automatically

**Author:** Bang Liu

**Date:** 2023-08-05

In this document, I will introduce how to automatically generate the documentation for your python project with several tools.

## Install libraries
We use the following python packages:

* [MkDocs](https://www.mkdocs.org/) for building static pages from Markdown
* [mkdocstrings](https://mkdocstrings.github.io/) for auto-generating documentation from docstrings in your code
* [Material](https://realpython.com/python-project-documentation-with-mkdocs/) for MkDocs for styling your documentation

```
pip install --upgrade pip
pip install mkdocs
pip install mkdocstrings
pip install mkdocs-material
```

You can install support for specific languages using extras, for example:

```
pip install 'mkdocstrings[crystal,python]'
```

Note: the support for specific languages are not installed by default, so I would recommend install by the above command.

## Create mkdocs project
Now assume you are in the root directory of your project:

```
mkdocs new .
```

You will see:

```
INFO    -  Writing config file: ./mkdocs.yml
INFO    -  Writing initial docs: ./docs/index.md
```

MkDocs comes with a built-in dev-server that lets you preview your documentation as you work on it. Make sure you're in the same directory as the ```mkdocs.yml``` configuration file, and then start the server by running the ```mkdocs serve``` command:

```
% mkdocs serve
INFO    -  Building documentation...
INFO    -  Cleaning site directory
WARNING -  Excluding 'README.md' from the site because it conflicts with
           'index.md'.
INFO    -  Documentation built in 0.08 seconds
INFO    -  [14:25:59] Watching paths for changes: 'docs', 'mkdocs.yml'
INFO    -  [14:25:59] Serving on http://127.0.0.1:8000/
INFO    -  [14:26:11] Browser connected: http://127.0.0.1:8000/
```

Open up [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser, and you'll see the default home page being displayed.

## Customize your mkdocs.yml
We can customize the style of our documentation. Edit the ./mkdocs.yml file:

```
site_name: your-project-name
site_url: your-project-website
nav:
  - Home: index.md
theme:
  name: "material"
```

This way, we can use the material theme. You can also use other themes [1,2].

## Add more markdown files to the documentation
As described in [1], we can follow the structure proposed in the Diátaxis documentation framework, which suggests splitting your documentation into four distinct parts:

* Tutorials
* How-To Guides
* Reference
* Explanation

Therefore, we can create these markdown files and put them into the ./docs/ folder. Then we edit our mkdocs.yml configuration file to add them:

```
site_name: your-project-name
site_url: your-project-website

nav:
  - index.md
  - tutorials.md
  - how-to-guides.md
  - reference.md
  - explanation.md

theme:
  name: "material"
```

We can also edit the titles for each page, adjust their order, and so on. See [1] for more details.

## Generate document from Docstrings
We need to use ```mkdocstrings``` package for this purpose.

MkDocs is a static-site generator geared toward writing documentation. However, you can’t fetch docstring information from your code using MkDocs alone. You can make it work with an additional package called mkdocstrings.

You already installed mkdocstrings into your virtual environment at the beginning of this tutorial, so you only need to add it as a plugin to your MkDocs configuration file:

```
site_name: your-project-name
site_url: your-project-website

plugins:
  - mkdocstrings

nav:
  - index.md
  - tutorials.md
  - how-to-guides.md
  - reference.md
  - explanation.md

theme:
  name: "material"
```

Now, to generate documentation from soruce code docstrings, we can select a markdown file, e.g., the reference.md file we have created, and put identifiers in it.

Mkdocstrings allows you to insert docstring information right into your Markdown pages using a special syntax of three colons (:::) followed by the code identifier that you want to document:

```
::: identifier
```
The identifier is a string identifying the object you want to document. The format of an ```identifier``` can vary from one handler to another. For example, the Python handler expects the full dotted-path to a Python object: ```my_package.my_module.MyClass.my_method``` [3]. 

The syntax to use identifier is:

```
::: identifier
    YAML block
```

See [https://mkdocstrings.github.io/usage/](https://mkdocstrings.github.io/usage/) for more details.

Basically, the YAML block is optional, and contains some configuration options.

For global options, we can put it in ```mkdocs.yml```. For example:

```
plugins:
- mkdocstrings:
    enabled: !ENV [ENABLE_MKDOCSTRINGS, true]
    custom_templates: templates
    default_handler: python
    handlers:
      python:
        options:
          show_source: false
```

And global configurations can be overridden by local configurations.


See [3] for more detailed tutorials. Briefly summarize, with mkdocstrings, we can use identifiers to gather the docstrings in our code and turn them into documentation.

**Tips:** Maintain a good coding style is very important. I prefer to use the docstring style listed here:
[https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)


## Automatically collect all the docstrings in a module

To avoid manually write the identifiers for each submodule/class/method in a markdown file to include the corresponding docstrings in our documentation, we can use the following option:

```
::: src.aeiva.agent
    options:
      show_submodules: true
```
The above example will automatically introduce all the docstrings in the aeiva.agent package into our documentation. 

## Advanced Theme Customization 
### Changing the logo and icons

See: [https://squidfunk.github.io/mkdocs-material/setup/changing-the-logo-and-icons/](https://squidfunk.github.io/mkdocs-material/setup/changing-the-logo-and-icons/)

### Customize the landing home page

We can further customize the home page of our documentation.

First, set your custom_dir in mkdocs.yml:

```
theme:
  custom_dir: docs/overrides
...

```
The above setting use overrides directory in docs/ as the custom directory.

We than copy all the contents in: [https://github.com/squidfunk/mkdocs-material/tree/master/src/.overrides](https://github.com/squidfunk/mkdocs-material/tree/master/src/.overrides)
to our ```docs/overrides/``` folder.

Next, in the front matter of your index.md, you need to specify the template to use (copy below to index.md):

```
---
title: Title
template: home.html
---
```
One important thing that took me a while to realize: you need a newline at the end of your md file. If you don't have one, the content will not display [6]. 

Finally, we can customize the ```home.html``` and ```main.html``` in the overrides folder to make it consistent with our project.


See [6] for a reference.

**Note:** I found the landing page on [https://squidfunk.github.io/mkdocs-material/](https://squidfunk.github.io/mkdocs-material/) is really fancy! It is based on Parallax Image Effect using html and css. To DIY the effect, I downloaded the source file of the webpage directly, and then replace all ```assets/images/layers/``` in the html source file with ```./Material for MkDocs_files/```. Because this is the only folder I can get with downloading. I haven't done with understanding and customizing the landing homepage based on this template. To be tested in the future. :) (I put this verion in docs/overrides-dev/)

## Organize your documentation

### Navbar nesting

You can add an additional level to your navbar like this:

```
nav:
  - Home: index.md
  - About: about.md
  - Foo:
      - Overview: foo/index.md
      - Bar: foo/bar.md
```

### Reference to another markdown file

In a markdown document, we can refer to another file from one file, like the following:

```
[How to generate project documentation automatically from docstrings](./GENERATE_DOCS.md)
```

## Deploy Your Documentation to GitHub

GitHub repositories automatically serve static content when committed to a branch named gh-pages. MkDocs integrates with that and allows you to build and deploy your project documentation in a single step:

```
mkdocs gh-deploy
```

Running this command rebuilds the documentation from your Markdown files and source code and pushes it to the gh-pages branch on your remote GitHub repository.

Because of GitHub’s default configuration, that’ll make your documentation available at the URL that MkDocs shows you at the end of your terminal output:

```
INFO - Your documentation should shortly be available at:
       https://user-name.github.io/project-name/
```


## Summarize
So we basically follow the following procedures to create our documentation:

1. Create virtual env for your project. Create your project. Create your github repository.
2. Install the libraries: mkdocs, mkdocstrings, mkdocs-material
3. Go to the project root directory.
4. Use mkdocs to create the docs. It will produce ```mkdocs.yml``` and ```./docs/index.md```.
5. Customize the ```mkdocs.yml```. Basically, this is the global setting of the documentation. See [2] for details. You can customize your documentation theme to ```materials``` theme that supported by ```mkdocs-material``` python package.
6. Customize the contents in ```./docs/```. Basically, you can create different markdown files here; you can automatically create documentation contents from docstrings of your code by using ```::: identifier``` that supported by ```mkdocstrings```. See [4] for details.
7. Customize the organization of your documentation. For example, you can use nested navigation; you can use cross-reference, etc.
8. Build your documentation using ```mkdocs build.
9. Host your documentation using ```mkdocs gh-deploy```. Your documentation should shortly be available at: ```https://user-name.github.io/project-name/```.

### More
Please read [1,2,3,4] for more detailed tutorials.

## Reference
[1] [Build Your Python Project Documentation With MkDocs](https://realpython.com/python-project-documentation-with-mkdocs/)

[2] [Getting Started with MkDocs](https://www.mkdocs.org/getting-started/)

[3] [mkdocstrings.github.io/](https://mkdocstrings.github.io/)

[4] [mkdocs-material/](https://github.com/squidfunk/mkdocs-material)

[5] [Diátaxis
A systematic approach to technical documentation authoring.](https://diataxis.fr/)

[6] [https://github.com/squidfunk/mkdocs-material/issues/1996](https://github.com/squidfunk/mkdocs-material/issues/1996)