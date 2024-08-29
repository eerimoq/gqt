all:
	ruff check .
	python3 -m unittest
