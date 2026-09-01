### §2.4 MCP — connecting external systems

2.4.1 What MCP (Model Context Protocol) is, from zero: a standard way for a separate process to
      expose tools, resources and prompts to an agent. Why a standard beats N bespoke integrations.
      `[ZERO]`
2.4.2 Transport shapes: stdio (local subprocess), HTTP/SSE (remote). What each implies for
      auth and failure. `[DOC]`
2.4.3 Where servers are registered and the scopes: user, project `.mcp.json`, local, plugin
      `.mcp.json`. `claude mcp add/list/remove`, `claude mcp login/logout`. `[DOC]`
2.4.4 Project-server approval and workspace trust; `enableAllProjectMcpServers`,
      `enabledMcpjsonServers`, `disabledMcpjsonServers`. `[DOC]`
2.4.5 `[TRAP]` `enabledMcpjsonServers` gates only servers declared in a project `.mcp.json` — it
      says nothing about user-scope registrations. Reading it to answer "which server is active"
      gives the wrong answer. This is a documented real mistake in the harness's own hook.
      `[TRAP]` `[CASE]`
