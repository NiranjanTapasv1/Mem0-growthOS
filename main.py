"""Mem0 GTM agent pipeline.

This script generates:
1. Realistic developer pain points around AI memory.
2. A short analysis of what each developer is struggling with.
3. Personalized, non-spammy outreach messages.
4. Three polished GTM content pieces for Mem0.

The primary path uses the new google-genai SDK (google.genai).
If the package or API key is unavailable, the script falls back to
a deterministic local generator so the pipeline still runs end to end.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Minimal .env fallback if python-dotenv is absent
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

MODEL_NAME = "gemini-2.0-flash"
OUTPUT_PATH = Path("outputs.md")
ROOT = Path(__file__).resolve().parent


@dataclass
class GeminiClient:
    """Light wrapper around the new google.genai client."""
    available: bool
    client: Any | None = None
    reason: str = ""


def load_api_key() -> str:
    """Load the Gemini API key from environment."""
    return (os.getenv("GEMINI_API_KEY") or "").strip()


def build_client(api_key: str) -> GeminiClient:
    """Initialize the new google.genai client."""
    if not api_key:
        return GeminiClient(available=False, reason="GEMINI_API_KEY is missing")

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        return GeminiClient(available=True, client=client)
    except ImportError:
        return GeminiClient(
            available=False,
            reason="google-genai is not installed. Run: pip install google-genai",
        )
    except Exception as exc:
        return GeminiClient(available=False, reason=str(exc))


def call_gemini(client: GeminiClient, prompt: str) -> str | None:
    """Call Gemini and return the raw text response, or None on failure."""
    if not client.available or client.client is None:
        return None
    try:
        from google import genai
        response = client.client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        text = response.text or ""
        return text.strip() or None
    except Exception as exc:
        print(f"  Gemini call failed: {exc}")
        return None


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the response in them."""
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def extract_json(text: str) -> Any | None:
    """Parse a JSON payload from a model response."""
    cleaned = strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        first_object = cleaned.find("{")
        first_array = cleaned.find("[")
        if first_object == -1 and first_array == -1:
            return None
        start = min(x for x in [first_object, first_array] if x != -1)
        end_candidates = [cleaned.rfind("}"), cleaned.rfind("]")]
        end = max(end_candidates)
        if end <= start:
            return None
        snippet = cleaned[start: end + 1]
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None


# ─── Fallback generators ────────────────────────────────────────────────────

def fallback_pain_points() -> list[dict[str, str]]:
    return [
        {
            "id": "1",
            "source": "Reddit",
            "title": "How are people keeping ChatGPT agents from forgetting everything?",
            "body": (
                "I'm building a support copilot and every thread starts over from zero. "
                "I tried stuffing the last few turns into the prompt, but the context gets messy fast. "
                "Has anyone found a practical way to keep the agent from forgetting user preferences and prior decisions?"
            ),
            "tone": "frustrated, practical",
            "technical_level": "intermediate",
            "use_case": "support copilot",
        },
        {
            "id": "2",
            "source": "GitHub Issue",
            "title": "Memory layer leaks personally identifiable data into unrelated sessions",
            "body": (
                "We rolled our own memory store with embeddings and a vector DB. It works until users share "
                "multiple projects, then the assistant starts pulling in the wrong facts. I need a safer way "
                "to remember stable preferences without cross-contaminating conversations."
            ),
            "tone": "technical, concerned",
            "technical_level": "advanced",
            "use_case": "multi-tenant SaaS assistant",
        },
        {
            "id": "3",
            "source": "Stack Overflow",
            "title": "Best pattern for persistent memory across AI chat sessions?",
            "body": (
                "I can store chat history in Postgres, but I still don't know how to decide what should be remembered, "
                "what should expire, and how to update old facts when a user changes their mind. "
                "Is there a standard pattern for this?"
            ),
            "tone": "curious, overwhelmed",
            "technical_level": "beginner",
            "use_case": "personal assistant prototype",
        },
        {
            "id": "4",
            "source": "X / Twitter",
            "title": "Spent two days building memory for my agent and it still feels dumb",
            "body": (
                "The hard part isn't storing the data. It's deciding what matters, when to retrieve it, and how to keep "
                "the assistant from hallucinating stale preferences. I feel like I'm rebuilding a whole subsystem "
                "just to make the agent act like it remembers me."
            ),
            "tone": "burned out, honest",
            "technical_level": "intermediate",
            "use_case": "consumer AI companion",
        },
        {
            "id": "5",
            "source": "Reddit",
            "title": "Need advice: memory for agentic workflow automation",
            "body": (
                "We have an agent that drafts follow-up emails, tickets, and summaries for sales reps. "
                "It keeps repeating context the rep already provided, and manual prompt hacks are getting unmaintainable. "
                "What are people using for durable memory here?"
            ),
            "tone": "ops-minded, deadline-driven",
            "technical_level": "intermediate",
            "use_case": "sales workflow automation",
        },
    ]


def fallback_analysis(pain_points: list[dict[str, str]]) -> list[dict[str, str]]:
    mapping = {
        "1": {
            "what_they_are_struggling_with": "Their support copilot needs continuity across threads without dragging the entire conversation history back in.",
            "what_they_probably_tried": "They probably tried bigger prompts, a short summary of the last few turns, and maybe embedding the whole thread.",
            "why_that_is_failing": "That approach breaks once the thread gets long because the assistant still cannot reliably recover stable preferences or decisions.",
            "empathy_note": "This is the classic looks easy until production memory problem.",
            "likely_next_step": "Separate durable user facts from transient chat history and retrieve only the relevant memory each turn.",
        },
        "2": {
            "what_they_are_struggling_with": "They need memory that is scoped correctly so facts from one project do not leak into another user session.",
            "what_they_probably_tried": "They likely tried a vector DB plus custom metadata filters and maybe a delete-by-user workaround.",
            "why_that_is_failing": "Raw embeddings are not enough here because the system still needs explicit update, dedupe, and isolation semantics.",
            "empathy_note": "This is the kind of bug that turns into trust issues fast.",
            "likely_next_step": "Use a memory layer that supports scoped storage, safe updates, and clean user-level separation.",
        },
        "3": {
            "what_they_are_struggling_with": "They know how to store chat logs but do not know how to decide what should persist, expire, or be rewritten.",
            "what_they_probably_tried": "They probably started with Postgres tables, then added a summary job, then got stuck on policy decisions.",
            "why_that_is_failing": "Storage alone does not tell the app what matters or how to refresh stale facts when the user changes something.",
            "empathy_note": "Beginners hit this wall because the missing part is the memory policy, not the database.",
            "likely_next_step": "Use a higher-level memory API so extraction, retention, and updates are handled consistently.",
        },
        "4": {
            "what_they_are_struggling_with": "Their consumer assistant needs to feel personal, but it keeps forgetting the exact preferences users care about.",
            "what_they_probably_tried": "They likely tried prompt hacks, hand-written memory rules, and summary-based retrieval.",
            "why_that_is_failing": "Those tricks do not solve the ranking problem, so stale preferences still surface at the wrong time.",
            "empathy_note": "Users notice this immediately because the product feels inattentive.",
            "likely_next_step": "Store durable preferences separately and retrieve them with a memory layer that knows what is still relevant.",
        },
        "5": {
            "what_they_are_struggling_with": "They need memory that works across repeated workflows like follow-ups, summaries, and ticket drafting.",
            "what_they_probably_tried": "They probably added custom prompt instructions and a few per-rep fields in their app database.",
            "why_that_is_failing": "That setup gets brittle once the same assistant handles multiple tasks and needs to reuse context consistently.",
            "empathy_note": "This is exactly the kind of internal tooling problem that grows into hidden engineering tax.",
            "likely_next_step": "Give the agent a durable memory layer so each workflow can pull only the relevant context.",
        },
    }
    return [{"id": item["id"], **mapping.get(item["id"], mapping["1"])} for item in pain_points]


def fallback_outreach(pain_points, analyses):
    outreach = []
    channel_map = {
        "GitHub Issue": "GitHub comment",
        "Stack Overflow": "Stack Overflow answer",
        "X / Twitter": "Reply on X",
    }
    messages = {
        "1": "This is the exact wall most support copilots hit. The model can answer but forgets the user between threads. Mem0 keeps durable memory outside the prompt so you pull back only stable preferences each turn. Worth trying with one user preference first and comparing against your current setup.",
        "2": "Cross-session leakage usually shows up after the first few real users so good catch early. Mem0 is built around scoped memory with clean user-level separation, which handles the isolation problem that raw embeddings cannot. I would prototype with hard user boundaries and see if the bad recall disappears.",
        "3": "You are already past the store chat history in Postgres stage which is where the real memory questions start. Mem0 gives you the memory abstraction instead of making you invent retention and update policy yourself. Start by testing whether it can persist one preference, expire one stale fact, and update one changed detail cleanly.",
        "4": "That feeling of built memory and it still feels dumb is usually a retrieval problem not a model problem. Mem0 keeps memory as a dedicated layer which makes it easier to surface the right preference instead of the last random summary. Measure whether your assistant can recall a preference after a few unrelated turns.",
        "5": "Workflow problems like this are exactly where prompt hacks stop scaling. Mem0 gives the agent durable memory so repeated workflows can reuse the right context without turning the prompt into a dump of everything the rep ever said. Try it on one workflow first like follow-up drafting.",
    }
    for item in pain_points:
        outreach.append({
            "id": item["id"],
            "channel": channel_map.get(item["source"], "Reddit comment"),
            "message": messages.get(item["id"], ""),
        })
    return outreach


def fallback_content():
    return {
        "linkedin_post": (
            "I spent three weeks trying to make an AI agent remember basic user preferences.\n\n"
            "The model was fine. The memory was the problem.\n\n"
            "I tried prompt stuffing, then rolling summaries, then a vector DB with custom retrieval. "
            "Each fix worked just enough to ship and then broke in exactly the places users notice most. "
            "The assistant would forget someone's name, repeat a question it asked yesterday, "
            "or surface a preference the user had changed two weeks ago.\n\n"
            "Then I found Mem0. Three lines of code. The memory problem became an infrastructure problem "
            "instead of a permanent engineering distraction.\n\n"
            "If you are building agents and your users keep having to re-explain themselves, "
            "you are not facing a model problem. You are facing a memory problem. Fix it properly."
        ),
        "blog_hook": (
            "Stop Building Memory Systems From Scratch\n\n"
            "Every AI team hits the same wall eventually. The model sounds impressive, "
            "then immediately forgets everything that mattered five minutes ago. "
            "You stack prompt hacks, rolling summaries, and vector search on top of each other "
            "and call it a memory system. It is not. It is a maintenance burden with good branding.\n\n"
            "The hard part was never storing chat logs. It is deciding what should persist, "
            "what should update when the user changes their mind, and how to retrieve the right fact "
            "at the right moment without dragging stale context back into the conversation. "
            "That problem keeps landing on application teams, and it is exactly why so many agents "
            "feel impressive in demos and fragile in production. There is a cleaner abstraction."
        ),
        "cold_email": (
            "Subject: memory infrastructure for your AI agents\n\n"
            "Hi [Name],\n\n"
            "If your team is building AI agents, memory will become a product problem fast. "
            "Most teams start with prompt hacks and a vector DB, then end up spending real engineering "
            "cycles on retrieval logic, deduplication, stale context, and update policies.\n\n"
            "Mem0 handles all of that through a simple API. Model agnostic, production ready, "
            "integrates in a few lines. Your team ships features instead of rebuilding memory infrastructure.\n\n"
            "Happy to send a quick code example if useful.\n\n"
            "Niranjan"
        ),
    }


# ─── Pipeline steps ─────────────────────────────────────────────────────────

def generate_pain_points(client: GeminiClient) -> list[dict[str, str]]:
    print("[1/4] Discovering developer pain points...")
    prompt = """
You are helping build a GTM agent for Mem0, a memory infrastructure product for AI apps.

Task: Generate 5 realistic developer pain points around AI memory.
Make them look like genuine posts from Reddit, GitHub issues, Stack Overflow, or X/Twitter.
Vary the tone, technical level, and use case.
Avoid marketing language. Make them feel like real developers venting or asking for help.

Return ONLY valid JSON as an array of 5 objects with these exact fields:
id, source, title, body, tone, technical_level, use_case
"""
    raw = call_gemini(client, prompt)
    if raw:
        parsed = extract_json(raw)
        if isinstance(parsed, list) and len(parsed) == 5:
            print("  Gemini generated pain points successfully.")
            return parsed
    print("  Using local fallback examples.")
    return fallback_pain_points()


def analyze_pain_points(client: GeminiClient, pain_points: list[dict]) -> list[dict]:
    print("[2/4] Analyzing pain points...")
    prompt = f"""
You are analyzing developer pain points for Mem0, a memory infrastructure startup.

Mem0 solves the problem that AI apps forget things between conversations.
It gives developers persistent intelligent memory with a simple API.

Pain points:
{json.dumps(pain_points, indent=2)}

For each, return an object with:
id, what_they_are_struggling_with, what_they_probably_tried,
why_that_is_failing, empathy_note, likely_next_step

Return ONLY valid JSON as an array of 5 objects.
"""
    raw = call_gemini(client, prompt)
    if raw:
        parsed = extract_json(raw)
        if isinstance(parsed, list) and len(parsed) == len(pain_points):
            print("  Gemini analyzed pain points successfully.")
            return parsed
    print("  Using local fallback analysis.")
    return fallback_analysis(pain_points)


def generate_outreach(client: GeminiClient, pain_points: list[dict], analyses: list[dict]) -> list[dict]:
    print("[3/4] Writing personalized outreach...")
    prompt = f"""
You are writing helpful outreach for developers struggling with AI memory.

Rules:
- Sound like a real developer responding in the thread, not a marketer
- Acknowledge their specific problem
- Mention Mem0 naturally and briefly
- Give one concrete next step
- Keep each message under 100 words

Pain points: {json.dumps(pain_points, indent=2)}
Analyses: {json.dumps(analyses, indent=2)}

Return ONLY valid JSON as an array of 5 objects with: id, channel, message
"""
    raw = call_gemini(client, prompt)
    if raw:
        parsed = extract_json(raw)
        if isinstance(parsed, list) and len(parsed) == len(pain_points):
            print("  Gemini wrote outreach successfully.")
            return parsed
    print("  Using local fallback outreach.")
    return fallback_outreach(pain_points, analyses)


def generate_content_pieces(client: GeminiClient, pain_points: list[dict], analyses: list[dict], outreach: list[dict]) -> dict:
    print("[4/4] Generating GTM content pieces...")
    prompt = f"""
You are writing GTM content for Mem0. Keep it human, specific, and non-corporate.

Mem0 is a memory infrastructure startup. It helps developers add persistent memory
to AI applications in a few lines of code. Model agnostic, production ready.

Use these pain points for tone and specificity:
{json.dumps(pain_points[:2], indent=2)}

Create these 3 pieces and return ONLY valid JSON with these exact keys:

linkedin_post: A first-person LinkedIn post. The writer is a developer who just
discovered Mem0 after weeks of struggling with memory. Genuine, specific, no
corporate language. Around 150 words.

blog_hook: Opening paragraph only for a post called Stop Building Memory Systems
From Scratch. Target audience is developers on Hacker News. Punchy and technical.
Around 150 words.

cold_email: Under 150 words. Direct email to a startup CTO building AI agents.
No fluff. Subject line included. Sign off as Niranjan.
"""
    raw = call_gemini(client, prompt)
    if raw:
        parsed = extract_json(raw)
        if isinstance(parsed, dict) and {"linkedin_post", "blog_hook", "cold_email"}.issubset(parsed.keys()):
            print("  Gemini generated content pieces successfully.")
            return parsed
    print("  Using local fallback content.")
    return fallback_content()


# ─── Rendering ───────────────────────────────────────────────────────────────

def render_markdown(pain_points, analyses, outreach, content) -> str:
    lines = []
    lines.append("# Mem0 GTM Agent Output")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 1. Developer Pain Points")
    lines.append("")
    for item in pain_points:
        lines.append(f"### {item['id']}. [{item['source']}] {item['title']}")
        lines.append(f"**Tone:** {item['tone']} | **Level:** {item['technical_level']} | **Use case:** {item['use_case']}")
        lines.append("")
        lines.append(f"> {item['body']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 2. Pain Analysis")
    lines.append("")
    for item in analyses:
        lines.append(f"### {item['id']}")
        lines.append(f"**Struggling with:** {item['what_they_are_struggling_with']}")
        lines.append("")
        lines.append(f"**Probably tried:** {item['what_they_probably_tried']}")
        lines.append("")
        lines.append(f"**Why it is failing:** {item['why_that_is_failing']}")
        lines.append("")
        lines.append(f"**Empathy note:** {item['empathy_note']}")
        lines.append("")
        lines.append(f"**Likely next step:** {item['likely_next_step']}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 3. Personalized Outreach Messages")
    lines.append("")
    for item in outreach:
        lines.append(f"### {item['id']} — {item['channel']}")
        lines.append("")
        lines.append(item["message"])
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 4. GTM Content Pieces")
    lines.append("")
    lines.append("### LinkedIn Post")
    lines.append("")
    lines.append(content["linkedin_post"])
    lines.append("")
    lines.append("### Technical Blog Hook")
    lines.append("")
    lines.append(content["blog_hook"])
    lines.append("")
    lines.append("### Cold Outreach Email")
    lines.append("")
    lines.append(content["cold_email"])
    lines.append("")

    return "\n".join(lines).strip() + "\n"


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 50)
    print("  Mem0 GTM Agent Pipeline")
    print("=" * 50)
    print("")

    api_key = load_api_key()
    client = build_client(api_key)

    if client.available:
        print(f"Gemini ready: {MODEL_NAME}")
    else:
        print(f"Gemini unavailable: {client.reason}")
        print("Running on local fallback data.")
    print("")

    pain_points = generate_pain_points(client)
    analyses = analyze_pain_points(client, pain_points)
    outreach = generate_outreach(client, pain_points, analyses)
    content = generate_content_pieces(client, pain_points, analyses, outreach)

    md = render_markdown(pain_points, analyses, outreach, content)
    OUTPUT_PATH.write_text(md, encoding="utf-8")

    print("")
    print(f"Done. Outputs saved to {OUTPUT_PATH.resolve()}")
    print("")
    print("--- CONTENT PREVIEW ---")
    print("")
    print("LinkedIn Post:")
    print(content["linkedin_post"])
    print("")
    print("Blog Hook:")
    print(content["blog_hook"])
    print("")
    print("Cold Email:")
    print(content["cold_email"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())