test:
	coverage run -m unittest
	coverage html

lint:
	pylint $$(git ls-files "*.py")

style:
	isort --force-single-line-imports .
