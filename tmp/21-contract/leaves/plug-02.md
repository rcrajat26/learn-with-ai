### §2.5 Plugins and marketplaces

2.5.5 `plugin.json` fields: `name` (also the skill namespace), `description`, `version`, `author`,
      `homepage`, `repository`, `license`, `dependencies`, `settings`. `[DOC]`
2.5.6 Version management: users receive updates only when `version` is bumped (command sources
      excepted); what happens when it is omitted. `[DOC]`
2.5.7 Namespacing: plugin skills are always `/<plugin>:<skill>`; plugin agents are
      `@agent-<plugin>:<name>`; project and user `agents/` **override** a same-named plugin agent,
      while plugin skills coexist rather than override. `[DOC]` `[TRAP]`
2.5.8 A plugin's `settings.json` supports only `agent` and `subagentStatusLine` today — enough for
      a plugin to change the default persona of the whole session. `[DOC]`
