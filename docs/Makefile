# Minimal makefile for Sphinx documentation
#
.PHONY: help serve clean Makefile

# You can set these variables from the command line.
SPHINXOPTS    = -W -j auto
SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
BUILDDIR      = build
GENDIR  	  = $(SOURCEDIR)/gen

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)


serve:
	python3 -m http.server --directory $(BUILDDIR)/html

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo
	@echo "To view files, run:"
	@echo
	@echo "\tpython3 -m http.server --directory $(BUILDDIR)/html"
	@echo
	@echo "Or"
	@echo
	@ echo "\tmake serve"
	@echo
	@echo "... and open a browser to http://localhost:8000/"
	@echo

# Clean built docs & generated source files
clean:
	rm -rf $(BUILDDIR)/*
	rm -rf $(GENDIR)/*
	rm -rf $(SOURCEDIR)/examples/.strmbrkr*
	rm -rf $(SOURCEDIR)/examples/kvs_dump*

# Build html without running examples
html-noplot:
	$(SPHINXBUILD) -D plot_gallery=0 -b html $(ALLSPHINXOPTS) $(SOURCEDIR) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."
