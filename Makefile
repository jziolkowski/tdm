check-and-fix:
	isort -l 100 --up .
	black -S -l 100 .
	flake8 .
