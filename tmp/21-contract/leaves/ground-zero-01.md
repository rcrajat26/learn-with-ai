### §0.1 What the thing on the other side actually is

0.1.1 A **large language model** is one function: text in, text out. It has no memory between
      calls, no filesystem, no network, no clock. Say this before anything else. `[ZERO]`
0.1.2 What "predicts the next token" means, stated without ML vocabulary: given the text so far,
      the model produces a probability distribution over what comes next, and one option is
      sampled. `[ZERO]`
0.1.3 A **token** is a chunk of text, roughly 3–4 characters of English or ~0.75 words; code
      tokenises worse than prose because of punctuation and identifiers. `[ZERO]` `[NUM]`
0.1.4 Count tokens for three concrete strings — an English sentence, a Java method, a minified JSON
      blob — and show the ratio differs. `[PROVE]` `[NUM]`
0.1.5 Why token counts matter at all: they are the unit of both **cost** and **the limit**. `[ZERO]`
0.1.6 **Determinism:** the same input does not reliably give the same output. Temperature and
      sampling in one paragraph, no maths. Contrast with a pure Java method. `[ZERO]` `[JAVA]`
0.1.7 What the model *cannot* do, exhaustively: it cannot read a file, run a command, remember
      yesterday, or check whether what it said is true. Everything it appears to do, something
      else did. `[ZERO]` `[TRAP]`
0.1.8 **Confabulation** ("hallucination"): why a wrong answer is produced with the same fluency as
      a right one, and why fluency is therefore worthless as a correctness signal. `[ZERO]` `[TRAP]`
0.1.9 **Training cutoff:** the model's knowledge has a date; anything after it must be supplied in
      the input. Why this alone motivates the whole rest of the guide. `[ZERO]`
0.1.10 Model naming as of 2026: the Claude 5 family (`claude-opus-5`, `claude-sonnet-5`,
       `claude-fable-5`) and Haiku 4.5 (`claude-haiku-4-5-20251001`); aliases `opus`/`sonnet`/
       `haiku`/`fable`; what a `[1m]` suffix means. `[DOC]` `[RESEARCH]` `[VERSION]`
0.1.11 Capability tiers as an engineering decision, not a brand: which tier for exploration, which
       for writing code, which for architecture judgment. Cost ratio stated. `[NUM]`
0.1.12 The word **agent**, defined precisely: a model plus a loop plus tools. Not a synonym for
       "chatbot", not a synonym for "AI". `[ZERO]`



