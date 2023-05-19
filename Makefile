all:
	$(MAKE) style
	$(MAKE) test

test:
	coverage run --include "gqt/*" -m unittest
	coverage html

lint:
	pylint $$(git ls-files "*.py")

style:
	isort --force-single-line-imports .
