install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload

lint:
	ruff check app scripts tests

format:
	black app scripts tests

test:
	pytest -q
