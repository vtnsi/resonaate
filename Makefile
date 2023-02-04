
.PHONY: all doc clean purge

# Default: Do nothing
all:

# Make docs and serve it as a webpage
doc:
	(cd docs && make html && make serve)

# For quickly cleaning up files
clean:
	rm -rf .mjolnir*
	rm -rf kvs_dump*
	rm -rf debugging/
	(cd docs && make clean)

# Clean everything
purge: clean
	rm -rf db/
