# Generating Documentation

## Building Docs

1. Install required packages:
   ```shell
   (resonaate) $ pip install sphinx sphinx_rtd_theme m2r2
   ```
1. Navigate into the **docs** directory:
   ```shell
   (resonaate) $ cd docs
   ```
1. Create Sphinx source files for entire package
   ```shell
   (resonaate) $ sphinx-apidoc -MPTefo source/modules ../src/resonaate
   ```
   - `-M`: module documentation written above sub-module documentation
   - `-P`: include "private" members in documentation
   - `-T`: don't create a table of contents file using `sphinx-apidoc`
   - `-e`: separate each module's documentation onto it's own page
   - `-f`: force overwriting of Sphinx source files
   - `-o`: where to output the Sphinx source files, created if it doesn't exist
1. Build the documentation
   ```shell
   (resonaate) $ make clean; make html
   ```
1. Open **docs/build/html/index.html** in a browser to view the documentation

## Files & Directories

- **Makefile** and **make.bat**: allows you to simply run `make [target]` to generate docs
- **source/conf.py**: Sphinx configuration script
- **source/index.rst**: documentation "entry point" - the main page
- **source/_static/**: directory to hold static files for documentation generation
- **source/_templates/**: directory to hold template files for documentation generation
- **source/modules/**: where the Sphinx sources files created by `sphinx-apidoc` are placed
- **build**: where the generated documentation lives

## TODO

 - [ ] Latex support?
 - [x] Add markdown support for README, etc.
 - [ ] Support building API & "ICD"
 - [ ] Finalize styling, write documentation style guide/rules
