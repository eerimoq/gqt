all:
	$(MAKE) test
	$(MAKE) style
	$(MAKE) lint

test:
	coverage run --include "gqt/*" -m unittest
	coverage html

lint:
	pylint $$(git ls-files "*.py")

style:
	isort --force-single-line-imports .
