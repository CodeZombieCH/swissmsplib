install:
	poetry install

outdated:
	poetry show --outdated

update:
	poetry update

format:
	poetry run black .
