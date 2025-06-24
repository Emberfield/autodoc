# Autodoc - Simple Code Intelligence

Analyze and search codebases using AI. No overengineering, just works.

## Quick Start

```bash
# Setup
./create_autodoc.sh
hatch env create
echo "OPENAI_API_KEY=sk-your-key" > .env

# Use
hatch run analyze ./my-project --save
hatch run search "authentication"
```

## Install in Other Projects

```bash
pip install /path/to/autodoc
# or after publishing
pip install autodoc
```

Then use:
```python
from autodoc import Autodoc

autodoc = Autodoc()
await autodoc.analyze("./src")
results = await autodoc.search("validation")
```

That's it!
