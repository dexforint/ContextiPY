```bash
uv venv
uv pip install -e .
uv run python -c "import pcontext; print(pcontext.__version__)"
uv run python -m pcontext
ls "$env:USERPROFILE\.pcontext"
```
