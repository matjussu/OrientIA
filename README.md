# OrientIA

Specialized French-orientation RAG system with label-based re-ranking, benchmarked against general-purpose LLMs.

Submitted to the INRIA AI Grand Challenge.

## Quick start

1. Copy `.env.example` to `.env` and fill in your keys.
2. Install dependencies: `pip install -r requirements.txt`
3. Collect data: `python -m src.collect.merge`
4. Build index: `python -m src.rag.index`
5. Run benchmark: `python -m src.eval.runner`

## Project structure

See `docs/superpowers/plans/2026-04-10-orientia-mvp.md` for the full implementation plan.

## License

MIT
