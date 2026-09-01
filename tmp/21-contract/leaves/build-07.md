### §4.6 A plugin

4.6.1 Package §4.2–§4.4 as a plugin: `.claude-plugin/plugin.json`, `skills/`, `agents/`,
      `hooks/hooks.json`. Test with `--plugin-dir`. `[BUILD]`
4.6.2 `claude plugin validate`, then `--strict`. Fix what it reports. `[BUILD]` `[PROVE]`
4.6.3 Publish it to a local marketplace: `.claude-plugin/marketplace.json`, `/plugin marketplace
      add`, `/plugin install`, `/reload-plugins`. `[BUILD]`
4.6.4 Bump `version` and prove an installed copy updates. `[BUILD]` `[PROVE]`
4.6.5 Add a `dependencies` entry on a second local plugin, and demonstrate both the unresolved
      state and the `claude plugin list --json` `errors` array that reveals it. `[BUILD]` `[PROVE]`
4.6.6 Diff vs the real one: the sdlc-harness plugin and marketplace — cross-marketplace
      dependency trust, `${CLAUDE_PLUGIN_ROOT}` path discipline, content-hash version nudging, and
      a bootstrap skill that provisions what a plugin cannot install declaratively.



