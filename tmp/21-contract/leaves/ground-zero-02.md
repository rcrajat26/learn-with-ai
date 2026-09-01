### §0.2 The context window, taught as a data structure

0.2.1 The **context window** is the maximum number of tokens one request may contain — input plus
      output together. It is a hard limit, not a soft one. `[ZERO]` `[NUM]`
0.2.2 Current sizes: 200K standard, 1M in the extended-context tier. What "1M context" costs
      relative to 200K. `[NUM]` `[RESEARCH]` `[VERSION]`
0.2.3 A request is an ordered **list of messages**, each with a role: `system`, `user`,
      `assistant`. Show the literal JSON of a two-turn conversation. `[ZERO]` `[DOC]`
0.2.4 The window is **not** a memory the model writes to. It is the argument list of the next
      call. Say it in those words. `[ZERO]` `[TRAP]`
0.2.5 `[JAVA]` The honest analogy: a stateless `@RestController` method that receives the entire
      conversation as its request body every time, and a client that keeps appending to that body.
      State where the analogy breaks (no session, no cookie, no server-side store). `[JAVA]`
0.2.6 Therefore: cost and latency scale with **conversation length**, not with the length of your
      last message. Work the arithmetic for a 10-turn vs 100-turn session. `[PROVE]` `[NUM]`
0.2.7 What happens at the limit: the request is rejected, or the harness compacts. Both, named.
      `[ZERO]`
0.2.8 **Prompt caching** in one paragraph: the unchanged prefix of a request can be reused at a
      fraction of the price, which is why appending is cheap and *editing the beginning* is not.
      `[NUM]` `[RESEARCH]`
0.2.9 The default cache time-to-live is 5 minutes; `promptCacheTtl` and `subagentPromptCacheTtl`
      change it. Why a 6-minute pause costs real money. `[NUM]` `[DOC]`
0.2.10 The **budget framing** the whole guide rests on: 200K window, autocompaction threshold, and
       what is left for actual work. State the arithmetic. `[NUM]` `[PROVE]`
0.2.11 The five things that consume the window before you type anything: system prompt, tool
       schemas, memory files, skill listing, environment/git snapshot. Forward-reference §3.1.
0.2.12 "It forgot" is almost never a bug: it means *never in context* or *compacted out*. The two
       are distinguished differently and fixed differently. `[TRAP]`



