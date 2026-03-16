# hf

I've been downloading and managing local AI models from HuggingFace for a while
now, and the workflow involves enough moving parts -- GGUF files, MLX weights,
LMStudio imports, Ollama modelfiles, llama-swap configs -- that I wrote `hf` to
keep it all straight.

It's a single Python script that handles the full lifecycle: downloading models
via `git clone` from HuggingFace, checking them out with Git LFS, finding the
best quantization available (preferring fp32 down through q2), hard-linking them
into LMStudio, creating Ollama modelfiles, and generating configuration for
llama-swap, GPTel, and LiteLLM.

## Getting started

With Nix:

```bash
nix develop    # enter the development shell
hf --help
```

Or if you just have Python 3.11+ and `requests`:

```bash
pip install requests
python hf.py --help
```

## What it does

**Downloading and checkout:**

```bash
hf download TheBloke/Mistral-7B-v0.1-GGUF
hf checkout path/to/model.gguf
```

**Finding the best quantization** (it walks the priority list -- fp32, fp16,
q8, q6, q5, q4, q3, q2):

```bash
hf gguf ~/Models/TheBloke_Mistral-7B-v0.1-GGUF
```

**Importing into other tools:**

```bash
hf import-lmstudio path/to/model.gguf
hf import-ollama path/to/model.gguf
```

**Generating server configs:**

```bash
hf build-yaml       # writes llama-swap.yaml
hf print-yaml       # prints to stdout
hf gptel            # GPTel (Emacs) config
hf litellm          # LiteLLM config
```

**Managing a running llama-swap server:**

```bash
hf models           # list loaded models
hf status           # current status
hf unload           # unload current model
hf logs             # stream server logs
```

**Housekeeping:**

```bash
hf pending          # what needs fetch/merge/link
hf sizes            # model sizes
hf duplicates       # models that exist in both MLX and GGUF
hf remote-only      # models on the server but not locally
```

## Configuration

Model-specific settings live in `~/Models/models.csv` with columns for name,
draft model, context size, temperature, min-p, top-p, aliases, and extra args.
These get picked up when generating llama-swap and LiteLLM configurations.

## Development

```bash
nix develop          # enter dev shell with all tools
lefthook install     # set up pre-commit hooks
nix flake check      # run all checks (lint, format, types, tests)
```

The pre-commit hooks run formatting checks, linting, type checking, and tests
in parallel. The same checks run in CI via GitHub Actions.
