.PHONY: install
install:
	pip install -U -e . -r dev-requirements.txt

.PHONY: test
test:
	tox $(ARGS)

.PHONY: format
format:
	black .

.PHONY: lint
lint:
	tox -e lint

.PHONY: docs
docs:
	mkdocs build

.PHONY: docs-serve
docs-serve:
	mkdocs serve

.PHONY: docs-tests
docs-tests:
	tox -e docs

.PHONY: clean
clean:
	rm -rf /tmp/tox/pytest-pyright
	rm -rf `find . -name __pycache__`
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -f .coverage
	rm -f .coverage.*
	rm -rf build
	rm -rf dist
	rm -f coverage.xml
