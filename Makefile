.DEFAULT_GOAL := help

install:  ## Install an editable version of this app
install:
	pipenv run pip install --editable .

uninstall:  ## Uninstall this app
	pipenv run pip uninstall -y git-migration

format:  ## Auto-format and check pep8
	yapf -i $$(find * -type f -name '*.py')
	flake8 ./app ./tests

test:  ## Run tests
	pytest
	flake8 ./app ./tests

dist: clean  ## Create a binary dist
	(cd $(BASE) && $(PYTHON) setup.py sdist)

clean:  ## Clean all temporary files
clean:
	pipenv --rm || true
	find * -type f -name *.pyc | xargs rm -f
	find * -type f -name *~ |xargs rm -f
	find * -type d -name __pycache__ |xargs rm -rf
	rm -rf *.egg-info
	rm -rf dist/
	rm -f *.csv
	rm -rf .cache/
	rm -rf .eggs/

reset: ## Remove all logs and folders with repo clones
	rm -rf logs/
	rm -rf migration_temp/
	rm -rf syncDirectory/

include scripts/help.mk  # Must be included last.