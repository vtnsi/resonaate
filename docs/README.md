# Generating Documentation

This file goes over how to generate the RESONAATE documentation and a quick explanation of the documentation structure and features.
RESONAATE uses `sphinx` ([docs][sphinx-docs]) to generate its documentation and it auto-deploys to GitLab Pages as a static website (to be added soon).

______________________________________________________________________

**Table of Contents**

- [Generating Documentation](#generating-documentation)
  - [Documentation Style](#documentation-style)
  - [Building The Documentation](#building-the-documentation)
  - [Files & Directories](#files--directories)

______________________________________________________________________

## Documentation Style

We strongly adhere to the [Divio] structure of documentation as it provides a more direct way for users and developers to find and consume information.
Also, while the documentation uses both [reST][rest-docs] and [Markdown][commonmark] to write pages, the following rules are strictly adhered to:

1. [MyST][myst-docs] is used whenever possible for writing documentation source files (**.md** files under **docs/source**)
1. Sphinx-style [reST][sphinx-rest] along with [napoleon] is used in source code docstrings
1. Repository-level documentation (README, CONTRIBUTING, LICENSE, etc.) is written in _basic_ [Markdown][commonmark]

We use the `autosummary` [extension][autosummary] to auto-generate our API documentation from the source code docstrings.
Please review the Sphinx-flavored [reST][sphinx-rest] and [napoleon] documentation before contributing code.

Here are a few other highlights of the documentation that should make writing it easier:

- Auto-deploying of a static site for hosting the documentation on GitLab Pages using **.gitlab/.gitlab-ci.yml**
- the API documentation is customized using Jinja2 templates from [here][jinja2-template]
- Custom **style.css** & **layout.html** to make dynamic horizontal scaling better
- [Mermaid] integration for easy diagrams and flowcharts
- Incorporation of LaTeX **.bib** file for improved referencing and citations: [link][sphinx-bib]
- Examples Gallery that is auto-generated directly from Python scripts: [link][sphinx-gallery]

## Building The Documentation

1. Install required packages:
   ```shell
   pip install -e .[doc]
   ```
1. Navigate into the **docs** directory:
   ```shell
   cd docs
   ```
1. Build the documentation using:
   ```shell
   make clean; sphinx-build -b html source build
   ```
   OR
   ```shell
   make clean; make html
   ```
1. Open **docs/build/html/index.html** in a browser to view the documentation

Users can see what other targets are available by using `make help`, but other targets are not guaranteed to look nice or even build

## Files & Directories

- **Makefile** and **make.bat**: allows you to simply run `make [target]` to generate docs
- **requirements.txt**: dependencies required for generating documentation
- **source/**: directory containing all documentation source files
  - **source/conf.py**: `sphinx` configuration script. Go here for sphinx or extension options.
  - **source/index.md**: documentation "entry point" - the front page. This is where the main TOC lives which points to all other doc pages
  - **source/\_static/**: holds static files (style sheets & images) for documentation generation
  - **source/\_templates/**: holds Jinja2 template files for documentation generation
  - **source/background**: holds Markdown source for describing, deriving, explaining background technical details for how RESONAATE and its algorithms work
  - **source/development/**: holds documentation necessary for developers of RESONAATE like how to complete merge requests, build documentation, etc.
  - **source/examples/**: holds formatted Python scripts that are automatically ran and generated into pages for the "Examples Gallery"
  - **source/intro/**: holds Markdown source for the "Getting Started" documentation which explains the basics of RESONAATE for new users and developers
  - **source/meta/**: holds metadata files like the software history, license, and bibliography as well as the RESONAATE citation list in **resonaate.bib**
  - **source/reference/**: holds Markdown source for the "Reference Material" documentation which goes over implementation details of RESONAATE and provides active explanations of how to use specific portions of the tool.
  - **source/gen/**: holds generated source documentation for both the API documentation and the Examples Gallery. This section should be cleaned before rebuilding the docs with `make clean`
- **build**: directory where the generated documentation is placed. This should be cleaned before rebuilding documentation using `make clean`

```{rubric} TODO

```

- [x] Migrate to better hierarchy
- [x] Make docs front page better
- [x] Add images for front page
- [x] Make API landing page better
- [x] Make API module template better
- [x] Make simple examples for how `TwoBody` works
- [x] Make docstrings reference technical background when applicable.
- [x] Make documentation README better with more instructions, explanation of features.
- [ ] Make initial tutorial going over minimal config, running example, plotting data (See Issue #147)
- [ ] Add docstrings for all packages so summaries have text (See Issue #6)
- [ ] Make examples that are more targeted towards stuff like MMAE, MC, Tasking (See Issue #146)
- [ ] Add technical background for astro, estimation, ... (See Issue #145)
- [ ] Make RESONAATE icon and favicon (See Isse #148)
- [ ] Add version switching to docs with GitLab Pages (See Issue #143)

[autosummary]: https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html
[commonmark]: https://commonmark.org/help/
[divio]: https://documentation.divio.com/introduction/
[jinja2-template]: https://stackoverflow.com/a/62613202
[mermaid]: https://mermaid-js.github.io/mermaid
[myst-docs]: https://myst-parser.readthedocs.io/en/latest/index.html
[napoleon]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[rest-docs]: https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html
[sphinx-bib]: https://sphinxcontrib-bibtex.readthedocs.io/en/latest/index.html
[sphinx-docs]: https://www.sphinx-doc.org/en/master/index.html
[sphinx-gallery]: https://sphinx-gallery.github.io/stable/index.html
[sphinx-rest]: https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html
