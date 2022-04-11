isort:
	isort -l 120 --up .

black-check:
	black -S -l 120 --check .

black:
	black -S -l 120 .

flake8:
	flake8 .

check-and-fix: isort black flake8

dev-setup:
	pip3 install --upgrade pip setuptools wheel
	pip3 install -r requirements.txt -r requirements_dev.txt


