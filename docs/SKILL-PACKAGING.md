# Skill packaging checks — 19 September 2026

This pass checked official packaging documentation, not the earlier literature review.

The Agent Skills specification defines a skill directory with `SKILL.md`, required name/description frontmatter, optional scripts/references/assets, and progressive loading. That supports a concise method with deterministic helpers kept off the ordinary prompt path.

Source: https://agentskills.io/specification

The OpenAI Codex skills URL currently redirects to the official Build skills guide. It documents explicit and implicit activation, repository-local `.agents/skills` directories, and optional `agents/openai.yaml` with `allow_implicit_invocation`. The release can be manually copied into that directory; discovery and a clean model-host session still require testing on the user's actual installation.

Sources: https://developers.openai.com/codex/skills and https://learn.chatgpt.com/docs/build-skills

The current guide also describes plugin distribution as a route for broader installation. A plugin wrapper is a later distribution choice, not a reason to require an MCP server or UI for this first local skill. A shell-executing host and persistent storage are the actual runtime prerequisites for the bundled implementation.

The skill folder is a portable instruction/resource package, not a universal callable API. Hosts differ in execution permissions, skill discovery, persistent filesystem access, subagent context inheritance, and model privacy policy. The prepared artifact protocol can stay the same while these bindings differ.

The main entry is 632 whitespace-delimited words including frontmatter. This is not a measured token count or an empirical context-cost guarantee. Referenced guides and schemas have additional cost when loaded. Runtime calls return compact summaries or requested views; code is executed, not loaded wholesale.
