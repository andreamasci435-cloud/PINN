.PHONY: test demo serve
PYTHON = .venv/bin/python

test:
	$(PYTHON) -m pytest -q
	$(PYTHON) -m ruff check canon tests

demo:
	$(PYTHON) main-2.py run --config configs/demo.json

serve:
	$(PYTHON) main-2.py serve --port 8765
