VENV_DIR = .venv

isort:
	$(VENV_DIR)/bin/isort -l 100 --up .

black-check:
	$(VENV_DIR)/bin/black -S -l 100 --check .

black:
	$(VENV_DIR)/bin/black -S -l 100 .

flake8:
	$(VENV_DIR)/bin/flake8 .

check-and-fix: isort black flake8

dev-setup:
	python3 -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install --upgrade pip wheel setuptools
	$(VENV_DIR)/bin/pip install -r requirements_dev.txt


