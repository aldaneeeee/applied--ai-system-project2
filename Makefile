# Convenience commands. Run `make help` for the list.
.PHONY: help install ingest demo ask eval test clean ui

PYTHON ?= python3

help:
	@echo "GroundedRAG - available commands:"
	@echo "  make install   Install dependencies"
	@echo "  make ingest    Build the retrieval index from data/docs"
	@echo "  make demo      Run a canned end-to-end demo"
	@echo "  make ask       Ask a question (Q=\"your question\")"
	@echo "  make eval      Run the evaluation harness on the gold Q&A set"
	@echo "  make test      Run the offline test suite"
	@echo "  make ui        Launch the Streamlit web UI"
	@echo "  make clean     Remove the built index and logs"

install:
	$(PYTHON) -m pip install -r requirements.txt

ingest:
	$(PYTHON) -m src.ragqa.cli ingest

demo:
	$(PYTHON) -m src.ragqa.cli demo

ask:
	$(PYTHON) -m src.ragqa.cli ask "$(Q)"

eval:
	$(PYTHON) -m src.ragqa.cli eval

test:
	$(PYTHON) -m pytest

ui:
	$(PYTHON) -m streamlit run app_streamlit.py

clean:
	rm -rf index logs
