install:
	uv sync

dev:
	uv run uvicorn main:app --reload

check:
	uv run python -c "from main import app; print('FastAPI app loaded OK')"
