### §2.4 MCP — connecting external systems

2.4.11 **LSP as the cheaper cousin**: `.lsp.json`, a language server, and precise symbol lookups
       instead of reading and grepping whole files. The argument is token cost, not correctness.
       `[DOC]`
2.4.12 `[CASE]` The harness enables three official LSP plugins (`pyright-lsp`, `typescript-lsp`,
       `jdtls-lsp`) and its `check-init.sh` nudges every session when the binaries are missing —
       explicitly framed as "cutting token usage on code-heavy tasks. Optional." `[CASE]`
2.4.13 `[BUILD]` Register one MCP server, measure `/context` before and after, then write a deny
       rule that blocks its write tools. `[BUILD]` `[PROVE]`



