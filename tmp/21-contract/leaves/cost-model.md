### §3.4 The cost model

3.4.1 What you are billed for: input tokens, output tokens, cache writes, cache reads. Four
      different prices. `[NUM]` `[RESEARCH]`
3.4.2 Per-model pricing and the ratio between tiers, as of the write date. `[NUM]` `[RESEARCH]`
3.4.3 Why conversation length dominates: the same prefix re-sent every turn, times turns. Work a
      full session's arithmetic. `[PROVE]` `[NUM]`
3.4.4 What caching changes, and the 5-minute default TTL as the reason a paused session costs
      more when resumed. `[NUM]`
3.4.5 Where a subagent's ~2× comes from, itemised. `[PROVE]` `[NUM]`
3.4.6 The three ceilings and their different failure shapes: `--max-turns` (agency),
      `--max-budget-usd` (money), subprocess timeout (wall clock). `[NUM]`
3.4.7 Reading cost out of a run: the `-p --output-format json` envelope's cost and token fields;
      `/cost`; `modelPricing` for contracted rates. `[DOC]` `[BUILD]`
3.4.8 `[PROVE]` Measure it: run one task inline and the same task via a subagent, and report both
      envelopes. `[PROVE]` `[BUILD]`
3.4.9 The judgment this all supports: an unbounded agent loop is an unbounded invoice, so ceilings
      are reliability engineering, not thrift. `[CASE]`



