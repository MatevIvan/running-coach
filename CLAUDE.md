@AGENTS.md

# Claude Code Adapter

Project skills are exposed under `.claude/skills/` as thin discovery proxies. When a proxy activates, read its referenced canonical `.agents/skills/<skill-name>/SKILL.md` completely and treat that canonical directory as the skill root for relative references, scripts, and assets.
