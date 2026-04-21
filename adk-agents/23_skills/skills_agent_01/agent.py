"""Skills (Topic 23) — skills_agent_01.

Demonstrates ADK's Skills feature — modular, self-contained units of
functionality that agents load on demand to handle specialised tasks.

Key concepts shown:
┌──────────────────────────────────────────────────────────────────────┐
│ Skill (file-based) SKILL.md + references/ → loaded from directory   │
│ Skill (in-code) models.Skill() → defined inline in Python           │
│ SkillToolset bundles skills and adds them to an agent               │
│ load_skill_from_dir reads the SKILL.md + L3 resources from disk     │
└──────────────────────────────────────────────────────────────────────┘

Why Skills instead of just putting everything in the system prompt?
- Context window efficiency: skill instructions are only injected when
  the skill is triggered by the LLM, not on every single turn.
- Modularity: skills can be shared across agents like libraries.
- Separation of concerns: domain knowledge lives in structured files,
  not scattered through agent code.

The three levels of a Skill (L1/L2/L3):
L1 — Frontmatter (name, description) → used for skill discovery
L2 — Instructions (SKILL.md body) → loaded when skill is triggered
L3 — Resources (references/, assets/) → loaded on demand within a skill

This agent has TWO skills:
1. expense_skill (file-based) — expense policy Q&A with reference docs
2. leave_skill (in-code) — leave policy defined inline as a Skill object

Run:
cd /Users/harshitjain3/Documents/Learning/AI/adk2/23_skills
adk web skills_agent_01

Try asking:
"What is the meal allowance per person?"
"How do I submit an expense claim?"
"Can I fly business class?"
"How many days of annual leave do I get?"
"What is the sick leave policy?"
"Can I carry over unused leave?"
"""

import pathlib

from google.adk.agents import LlmAgent
from google.adk.skills import load_skill_from_dir, models
from google.adk.tools import skill_toolset

# ---------------------------------------------------------------------------
# Skill 1: File-based — loads from skills/expense_skill/
# ---------------------------------------------------------------------------
# The directory must follow the Agent Skill specification:
# SKILL.md → required (L1 frontmatter + L2 instructions)
# references/ → optional L3 reference files
# assets/ → optional L3 assets
# scripts/ → optional L3 executable scripts
#
# load_skill_from_dir reads SKILL.md and makes references/ available so
# the LLM can load them on demand using the load_resource tool.
# ---------------------------------------------------------------------------
_skills_dir = pathlib.Path(__file__).parent / "skills"

expense_skill = load_skill_from_dir(_skills_dir / "expense-skill")

# ---------------------------------------------------------------------------
# Skill 2: In-code — defined as a Skill object in Python
# ---------------------------------------------------------------------------
# Use this approach when:
# - The knowledge is short enough to inline
# - You want to generate skill content dynamically at runtime
# - You don't want filesystem dependencies
# ---------------------------------------------------------------------------
leave_skill = models.Skill(
    frontmatter=models.Frontmatter(
        name="leave-skill",
        description=(
            "Answers questions about employee leave policy — annual leave, "
            "sick leave, parental leave, carry-over rules, and how to apply."
        ),
    ),
    instructions=(
        "You are a leave policy assistant. Answer questions about leave entitlements "
        "precisely using the policy rules below.\n\n"
        "## Annual Leave\n"
        "- Employees get 20 days per year (pro-rated for part-time).\n"
        "- Leave accrues monthly (1.67 days/month).\n"
        "- Must be approved by manager at least 2 weeks in advance for >3 days.\n"
        "- Same-day or next-day leave requires manager notification but no advance approval.\n\n"
        "## Sick Leave\n"
        "- 10 days per year, non-accruing (does not roll over).\n"
        "- A doctor's note is required for absences longer than 3 consecutive days.\n"
        "- Sick leave cannot be taken as annual leave and vice versa.\n\n"
        "## Parental Leave\n"
        "- Primary caregiver: 16 weeks fully paid.\n"
        "- Secondary caregiver: 4 weeks fully paid.\n"
        "- Must notify HR at least 8 weeks before the expected start date.\n\n"
        "## Carry-Over Rules\n"
        "- Up to 5 unused annual leave days can be carried over to the next year.\n"
        "- Carried-over days must be used by March 31 or they are forfeited.\n"
        "- Sick leave does NOT carry over.\n\n"
        "## How to Apply\n"
        "1. Log in to the HR portal at hr.company.com.\n"
        "2. Click 'Request Leave' and select the leave type and dates.\n"
        "3. Add a note for the manager (optional but recommended).\n"
        "4. Submit — your manager receives an email to approve or decline.\n"
        "5. You will be notified by email once a decision is made.\n\n"
        "Always encourage employees to check their leave balance in the HR portal "
        "before submitting a request."
    ),
    resources=models.Resources(
        references={
            "carry_over_policy.md": (
                "# Carry-Over Policy Details\n\n"
                "Carry-over is calculated on December 31 each year. "
                "Employees receive an email in November reminding them of "
                "unused leave. The maximum carry-over is 5 days regardless "
                "of how many days were unused. Carry-over days appear as a "
                "separate balance in the HR portal labelled 'Carry-Over'."
            )
        }
    ),
)

# ---------------------------------------------------------------------------
# SkillToolset — bundles both skills and exposes them to the agent
# ---------------------------------------------------------------------------
# The agent sees skills as tools it can invoke by name.
# Only the L1 description is in the main prompt; L2 instructions are
# injected only when the skill is triggered — saving context window space.
# ---------------------------------------------------------------------------
hr_skill_toolset = skill_toolset.SkillToolset(skills=[expense_skill, leave_skill])

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------
root_agent = LlmAgent(
    name="skills_agent",
    model="gemini-2.0-flash",
    description="An HR assistant that uses Skills to answer expense and leave policy questions.",
    instruction=(
        "You are a helpful HR assistant. "
        "You have access to two Skills:\n"
        "1. expense-skill — for questions about expense claims, receipts, limits, and reimbursement.\n"
        "2. leave-skill — for questions about annual leave, sick leave, parental leave, and carry-over.\n\n"
        "Use the appropriate skill for each question. "
        "If a question is unrelated to expenses or leave, politely say you can only help with HR policy topics."
    ),
    tools=[hr_skill_toolset],
)
