# Skill Creator Best Practices Checklist

Based on Anthropic's official skill-creator documentation for Claude Code.
Source: https://github.com/anthropics/claude-code/blob/main/plugins/plugin-dev/skills/

---

## 1. Frontmatter & Metadata

### Required Fields
- `description`: One-line description of when to use the skill (used for trigger matching)

### Description Best Practices
- Use natural phrases that match how users actually talk
- Include action verbs: "create", "generate", "analyze", "improve", "fix"
- Include synonyms: if the skill "generates", also mention "create", "build"
- Keep under 200 characters
- Be specific enough to avoid false triggers on unrelated requests
- Be broad enough to catch all valid invocations

### Anti-patterns
- Too vague: "A useful development tool" (triggers on everything)
- Too narrow: "Generate a REST API endpoint for Express.js" (misses valid uses)
- Technical jargon only: "Execute SDD phase-2 pipeline" (users don't talk like this)


## 2. Directory Structure

### Recommended Layout
```
skill-name/
├── SKILL.md              # Core instructions (lean, essential)
├── references/           # Deep knowledge, patterns, guides
│   ├── patterns.md       # Common patterns and approaches
│   └── advanced.md       # Advanced techniques, edge cases
├── examples/             # Concrete output examples
│   ├── example-basic.md  # Simple/common case
│   └── example-complex.md# Complex/edge case
├── scripts/              # Validation, automation
│   └── validate.sh       # Check output quality/structure
└── template.md           # Output template (if skill generates files)
```

### When Each Directory is Needed
- **references/**: When SKILL.md exceeds ~1800 words or has specialized knowledge sections
- **examples/**: When the skill produces structured output (files, plans, stories, code)
- **scripts/**: When the skill's output can be programmatically validated
- **assets/**: When the skill needs static resources (schemas, configs, images)

### Anti-patterns
- Everything in a single SKILL.md file (context overload)
- Empty directories (noise)
- Generic example files that don't match real usage


## 3. Progressive Disclosure

### Principle
Keep SKILL.md lean (~1800 words max for core content). Move detailed/specialized knowledge
to `references/` files that Claude loads only when needed.

### What Stays in SKILL.md
- Frontmatter with description
- Brief skill overview (1-2 sentences)
- "When to Use" section with ideal scenarios
- Step-by-step procedure (the main flow)
- Important notes / guardrails
- Language section
- References to supporting files ("See `references/patterns.md` for detailed patterns")

### What Moves to references/
- Detailed explanations of specific techniques
- Lookup tables with many entries
- Domain-specific knowledge that's only needed in certain cases
- Advanced or edge-case handling
- Background context that supports but isn't core to the procedure

### How to Reference
Add an "Additional Resources" section at the end of SKILL.md:
```markdown
## Additional Resources

### Reference Files
- **`references/patterns.md`** — Detailed patterns for [topic]
- **`references/advanced.md`** — Advanced techniques for [topic]

### Examples
- **`examples/example-basic.md`** — Basic output example
- **`examples/example-complex.md`** — Complex scenario example
```


## 4. Content Quality (Written for Claude)

### Key Principle
The skill is being created for another instance of Claude to use. Focus on information that is
**beneficial and non-obvious** to Claude.

### What to Include
- **Procedural knowledge**: Step-by-step instructions with clear sequencing
- **Domain-specific details**: Things Claude wouldn't know from general training
- **Decision criteria**: When to choose option A vs option B
- **Stop/ask conditions**: When to pause and ask the user instead of proceeding
- **Failure modes**: What can go wrong and how to recover
- **Validation rules**: How to verify output quality

### What NOT to Include
- General knowledge Claude already has (how to write JSON, what REST is, etc.)
- Obvious instructions ("be careful", "think step by step")
- Verbose explanations when a clear instruction suffices
- Aspirational content ("in the future, we could...")

### Instruction Clarity
- Use numbered steps for sequential procedures
- Use bullet points for non-ordered lists
- Bold key terms and action words
- Use code blocks for file paths, commands, and format examples
- Be explicit about what files to read and write
- Specify exact file names and paths when possible


## 5. Examples & Reusable Resources

### Why Examples Matter
Concrete examples are the single most impactful resource for skill quality. Claude produces
significantly better output when it has a reference example to pattern-match against.

### Good Examples
- Based on real-world usage (anonymized if needed)
- Show both input and expected output
- Cover the common case AND at least one edge case
- Include enough context to understand the example without external knowledge
- Are properly formatted as the skill's output would be

### Example File Naming
- `example-basic.md` — The simplest, most common case
- `example-with-figma.md` — Variant with Figma integration
- `example-monorepo.md` — Variant for monorepo projects

### Anti-patterns
- Toy examples that don't reflect real usage
- Examples without context ("Here's an output" with no explanation of the input)
- Only showing the happy path


## 6. Robustness & Error Handling

### Input Validation
- Check that required files exist before proceeding
- Validate file format (e.g., frontmatter is valid YAML)
- Handle missing optional inputs gracefully

### Prerequisites
- Check for required tools/MCPs before using them
- Provide clear install instructions when prerequisites are missing
- Offer graceful degradation (manual fallback when automation isn't available)

### Stop/Ask Conditions
- Define clear points where the skill should stop and ask the user
- Never proceed with ambiguous inputs — ask for clarification
- Limit clarification rounds (e.g., max 2 rounds of 3 questions)

### Failure Recovery
- When a step fails, provide actionable error messages
- Suggest specific fixes, not generic "something went wrong"
- When appropriate, offer to retry with different parameters


## 7. Iteration Workflow

### The Improvement Cycle
1. **Use** the skill in real-world tasks
2. **Identify** where it struggles or produces poor output
3. **Determine** which part of SKILL.md or resources needs updating
4. **Implement** the changes
5. **Test** the skill again on the same tasks

### Common Improvements
- Strengthen trigger phrases in the description
- Move lengthy sections from SKILL.md to references/
- Add missing examples for edge cases
- Clarify ambiguous instructions
- Add explicit handling for failure modes users encountered
- Improve output templates based on real usage patterns
