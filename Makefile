# Convenience commands. Run `make help` for the list.
.PHONY: help install run ask eval test ui clean

PYTHON ?= python3

help:
	@echo "Music Recommender + AI DJ"
	@echo "  make install   Install dependencies"
	@echo "  make run       Original Module 3 demo (fixed pop/happy profile)"
	@echo "  make ask Q=\"chill lofi for studying\"   Ask the AI DJ"
	@echo "  make eval      Run the reliability evaluation"
	@echo "  make test      Run the test suite (offline, no key needed)"
	@echo "  make ui        Launch the Streamlit web UI"
	@echo "  make clean     Remove logs and caches"

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m src.main

ask:
	$(PYTHON) -m src.main --ask "$(Q)" --trace

eval:
	$(PYTHON) -m src.evaluate

test:
	$(PYTHON) -m pytest

ui:
	$(PYTHON) -m streamlit run app.py

clean:
	rm -rf logs .pytest_cache src/__pycache__ tests/__pycache__
