install:
	poetry install

outdated:
	poetry show --outdated

update:
	poetry update

format:
	poetry run isort .
	poetry run black --target-version py314 .
