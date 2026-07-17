.PHONY: setup test demo serve smoke clean

setup:
	bash setup.sh

test:
	.venv/bin/python -m pytest -q

demo:
	.venv/bin/python examples/demo_seed.py

smoke:
	.venv/bin/python scripts/mcp_smoke.py

serve:
	.venv/bin/construction-mcp

clean:
	rm -rf .venv data *.egg-info .pytest_cache __pycache__ construction_mcp/__pycache__ tests/__pycache__
