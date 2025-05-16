.PHONY: tests

tests:
	PYTHONPATH=src pytest $(ARGS)
