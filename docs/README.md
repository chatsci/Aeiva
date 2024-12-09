


# docs
This folder is the place where we put materials related to generating  our documentation website. Currently we use `mkdocs` for this purpose. To adjust the website, we need to revise the files within `./overrides-material/`.

To adjust the menu bar of the website, revise `../mkdocs.yml`.


To build the site, run:

```shell
mkdocs build
```
It will generate `../site/` folder that contains the website files.

To test locally, run:

```shell
mkdocs serve
```

To deploy with GitHub pages, run:

```shell
mkdocs gh-deploy
```

More details, see: https://www.mkdocs.org/