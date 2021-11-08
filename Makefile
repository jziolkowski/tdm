isort:
	isort -l 100 --up .

black-check:
	black -S -l 100 --check .

black:
	black -S -l 100 .

flake8:
	flake8 .

check-and-fix: isort black flake8

dev-setup:
	pip3 install --upgrade pip setuptools wheel
	pip3 install -r requirements.txt -r requirements_dev.txt


