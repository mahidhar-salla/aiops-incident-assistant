# Roadmap

v0.1.0 (this release): synthetic incidents, redaction, BM25 runbook retrieval, mock/Ollama/Bedrock backends, grounding check, eval harness.

Next, roughly in order:

- [ ] Alert grouping: cluster raw alerts into candidate incidents by time window, service and signature (no LLM).
- [ ] Semantic grounding: check that each cited line actually supports its claim (entailment with a small model), not just that it exists.
- [ ] Run the eval on a larger local model and on Bedrock, and publish the numbers next to the 1.5B baseline.
- [ ] Harder incidents: cascades where the loudest service isn't the cause, and two overlapping faults.
- [ ] Post-incident write-up mode: draft a blameless review skeleton from the brief plus the human's notes.
- [ ] Optional embeddings retrieval behind the same interface, compared against BM25 in the eval.
