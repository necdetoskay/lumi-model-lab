# Trendyol LLM 8B T1 initial run note

The first frozen-story run is preserved as negative evidence, but it does **not** represent the intended `/no_think` protocol cleanly.

Observed first-run evidence:
- 2,057 words (inside nominal 1,600–2,400 band)
- 5,200 / 5,200 output tokens
- token-limit hit
- ended_with_eos = false
- 340.448 s runtime
- 6.641 GB peak allocated VRAM
- output visibly entered repetitive long-form looping
- decoded output begins with a `<think>` block even though the YAML requested `enable_thinking: false`

Harness finding:
`src/local_fastmodel_baseline.py` read the `enable_thinking` field from YAML only as ordinary generation metadata and did not forward it to `tokenizer.apply_chat_template(...)`. Therefore the model actually ran in thinking mode.

A second harness issue was also corrected for the controlled retest: the original config declared `max_seq_length: 4096` while allowing 5,200 new tokens plus the input prompt. The corrected retest uses an 8,192 sequence length and a separate output directory so the first-run evidence is not overwritten.

Decision:
Do not reject or promote the model from the first story. Run exactly one corrected no-think / 8K-context retest first. Only if that output is stable, complete and materially better should the experiment expand to five frozen stories.
