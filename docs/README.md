# Documentation

This file goes over the RESONAATE documentation system including its structure and features and how to build the documentation.
RESONAATE uses [sphinx](https://www.sphinx-doc.org/en/master/index.html) to generate its documentation along with [MyST](https://myst-parser.readthedocs.io/en/latest/index.html) as its parser.

**NOTE**: This document is better viewed in the official HTML documentation
Please see [Building the Documentation](#building-the-documentation) for instructions.

______________________________________________________________________

<!-- START TOC -->

<!-- TOC Formatted for GitLab -->

**Table of Contents**

\[\[_TOC_\]\]

<!-- END TOC -->

______________________________________________________________________

## Documentation Style

We strongly adhere to the [Divio] structure of documentation as it provides a more direct way for users and developers to find and consume information.
Also, while the documentation uses both [reST][rest-docs] and [Markdown][commonmark] to write pages, the following rules are strictly adhered to:

1. [MyST][myst-docs] is used whenever possible for writing documentation source files (**.md** files under **docs/source**)
1. Sphinx-style [reST][sphinx-rest] along with [napoleon] is used in source code docstrings
1. Repository-level documentation (`README.md`, `CONTRIBUTING.md`, `LICENSE`, etc.) is written in [GitLab Flavored][glfm] Markdown

It is **highly** recommended that users review both the [sphinx][sphinx-docs] and [myst][myst-docs] documentation for how to format documentation source files.

## Features

We use the `autosummary` [extension][autosummary] to auto-generate our API documentation from the source code docstrings.
Please review the Sphinx-flavored [reST][sphinx-rest] and [napoleon] documentation before contributing code.

Here are a few other highlights of the documentation that should make writing it easier:

- Auto-build and serve the documentation locally using `make html` & `make serve`
- the API documentation is customized using Jinja2 templates from [here][jinja2-template]
- Custom **style.css** & **layout.html** to make dynamic horizontal scaling better
- [Mermaid] integration for easy diagrams and flowcharts
- Incorporation of LaTeX **.bib** file for improved referencing and citations: [link][sphinx-bib]
- Examples Gallery that is auto-generated directly from Python scripts: [link][sphinx-gallery]

## Building The Documentation

To install documentation dependencies:

```bash
pip install -e .[doc]
pre-commit install
```

Or to install all development dependencies:

```bash
make install
```

Once the dependencies are installed, you can execute this from the repo root to build the documentation:

```bash
make doc
```

- Open [http://localhost:8000/](http://localhost:8000/) in a browser

Users can see what other targets are available by using `make help`, but other targets are not guaranteed to look nice or even build.

## Layout

- **Makefile**: allows you to simply run `make [target]` to generate docs
- **source/**: directory containing all documentation source files
  - **conf.py**: `sphinx` configuration script. Go here for sphinx or extension options.
  - **index.md**: documentation "entry point" - the front page. This is where the main TOC lives which points to all other doc pages
  - **\_static/**: holds static files (style sheets & images) for documentation generation
  - **\_templates/**: holds Jinja2 template files for documentation generation
  - **background/**: holds Markdown source for describing, deriving, explaining background technical details for how RESONAATE and its algorithms work
  - **development/**: holds documentation necessary for developers of RESONAATE like how to complete merge requests, build documentation, etc.
  - **examples/**: holds formatted Python scripts that are automatically ran and generated into pages for the "Examples Gallery"
  - **intro/**: holds Markdown source for the "Getting Started" documentation which explains the basics of RESONAATE for new users and developers
  - **meta/**: holds metadata files like the software history, license, and bibliography as well as the RESONAATE citation list in **resonaate.bib**
  - **reference/**: holds Markdown source for the "Reference Material" documentation which goes over implementation details of RESONAATE and provides active explanations of how to use specific portions of the tool.
  - **gen/**: holds generated source documentation for both the API documentation and the Examples Gallery. This section should be cleaned before rebuilding the docs with `make clean`
- **build**: directory where the generated documentation is placed. This should be cleaned before rebuilding documentation using `make clean`

## To Do

- [x] Migrate to better hierarchy
- [x] Make docs front page better
- [x] Add images for front page
- [x] Make API landing page better
- [x] Make API module template better
- [x] Make simple examples for how `TwoBody` works
- [x] Make docstrings reference technical background when applicable.
- [x] Make documentation README better with more instructions, explanation of features.
- [x] Add docstrings for all packages, so summaries have text
- [ ] Make initial tutorial going over minimal config, running example, plotting data (See Issue [#54])
- [ ] Make examples that are more targeted towards stuff like MMAE, MC, Tasking (See Issue [#55])
- [ ] Add technical background for astro, estimation, ... (See Issue [#56])
- [ ] Make RESONAATE icon and favicon (See Issue [#53])

[#53]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues/53
[#54]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues/54
[#55]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues/55
[#56]: https://code.vt.edu/space-research/resonaate/resonaate/-/issues/56
[autosummary]: https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html
[commonmark]: https://commonmark.org/help/
[divio]: https://documentation.divio.com/introduction/
[glfm]: https://docs.gitlab.com/ee/user/markdown.html
[jinja2-template]: https://stackoverflow.com/a/62613202
[mermaid]: https://mermaid-js.github.io/mermaid
[myst-docs]: https://myst-parser.readthedocs.io/en/latest/index.html
[napoleon]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[rest-docs]: https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html
[sphinx-bib]: https://sphinxcontrib-bibtex.readthedocs.io/en/latest/index.html
[sphinx-docs]: https://www.sphinx-doc.org/en/master/index.html
[sphinx-gallery]: https://sphinx-gallery.github.io/stable/index.html
[sphinx-rest]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html
