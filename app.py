"""Flask web app for the Mem0 GrowthOS dashboard."""

from __future__ import annotations

import json
import os
import socket
import traceback
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

from main import (
    analyze_pain_points,
    build_client,
    call_gemini,
    extract_json,
    generate_content_pieces,
    generate_outreach,
    generate_pain_points,
    load_api_key,
)


app = Flask(__name__)
OUTPUT_PATH = Path("outputs.md")
LAST_SESSION_STATE: dict[str, Any] = {}


def is_port_available(host: str, port: int) -> bool:
    """Return True when the port can be bound on the requested host."""

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex((host, port)) != 0


def choose_port(preferred_port: int = 5000, host: str = "127.0.0.1") -> int:
    """Pick the first available port starting from the preferred one."""

    env_port = os.getenv("PORT")
    if env_port:
        try:
            preferred_port = int(env_port)
        except ValueError:
            pass

    for port in range(preferred_port, preferred_port + 20):
        if is_port_available(host, port):
            return port
    raise RuntimeError(f"No free port found starting at {preferred_port}")


def make_client():
    """Create a Gemini client or a fallback wrapper."""

    return build_client(load_api_key())


def enrich_analyses(pain_points: list[dict[str, Any]], analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach pain point titles to the analysis payload for easier rendering."""

    title_map = {item["id"]: item["title"] for item in pain_points}
    enriched: list[dict[str, Any]] = []
    for analysis in analyses:
        item = dict(analysis)
        item["title"] = title_map.get(analysis["id"], f"Signal {analysis['id']}")
        enriched.append(item)
    return enriched


def normalize_source(source: str) -> str:
    mapping = {
        "Reddit": "reddit",
        "GitHub Issue": "github",
        "Stack Overflow": "stackoverflow",
        "X / Twitter": "x",
    }
    return mapping.get(source, "other")


def urgency_label(score: int) -> str:
    if score >= 8:
        return "Critical"
    if score >= 6:
        return "High"
    if score >= 3:
        return "Medium"
    return "Low"


def urgency_class(score: int) -> str:
    if score >= 8:
        return "urgent"
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def compute_urgency_score(signal: dict[str, Any], analysis: dict[str, Any], index: int) -> int:
    text = " ".join(
        str(signal.get(key, ""))
        for key in ("title", "body", "tone", "technical_level", "use_case")
    ).lower()
    text += " " + " ".join(str(analysis.get(key, "")) for key in ("why_that_is_failing", "what_they_probably_tried")).lower()

    score = 4 + (index % 3)
    if signal.get("source") == "GitHub Issue":
        score += 1
    if signal.get("source") == "Stack Overflow":
        score += 1
    for keyword, weight in (
        ("urgent", 2),
        ("broken", 2),
        ("leak", 3),
        ("forget", 1),
        ("stale", 1),
        ("multi-tenant", 2),
        ("pii", 3),
        ("production", 1),
        ("trust", 1),
        ("can't", 1),
        ("cannot", 1),
    ):
        if keyword in text:
            score += weight
    return max(1, min(10, score))


def create_signal_records(
    pain_points: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Decorate raw pain points with urgency, timestamps, and render-friendly metadata."""

    analysis_map = {item["id"]: item for item in analyses}
    now = datetime.now()
    signals: list[dict[str, Any]] = []

    for index, pain_point in enumerate(pain_points):
        analysis = analysis_map.get(pain_point["id"], {})
        score = compute_urgency_score(pain_point, analysis, index)
        created_at = now - timedelta(minutes=index * 7 + 3)
        signal = {
            **pain_point,
            "analysis": analysis,
            "urgency_score": score,
            "urgency_label": urgency_label(score),
            "urgency_class": urgency_class(score),
            "source_key": normalize_source(pain_point.get("source", "")),
            "timestamp": created_at.strftime("%b %d, %I:%M %p"),
            "relative_time": "just now" if index == 0 else f"{index * 3 + 2}m ago",
            "preview": pain_point.get("body", "")[:220].rstrip(),
            "saved": score >= 6 or index < 3,
        }
        signals.append(signal)

    if not any(signal["saved"] for signal in signals):
        for signal in signals[:3]:
            signal["saved"] = True

    return signals


def summary_metrics(signals: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate the top-line metrics for the dashboard."""

    if not signals:
        return {
            "total_signals": 0,
            "critical_count": 0,
            "average_urgency": 0,
            "sources_active": 0,
            "most_active_source": "None",
            "top_use_case": "None",
            "average_developer_level": "None",
            "use_case_distribution": [],
            "source_distribution": [],
        }

    source_counts = Counter(signal["source"] for signal in signals)
    use_case_counts = Counter(signal["use_case"] for signal in signals)
    level_map = {"beginner": 1, "intermediate": 2, "advanced": 3}
    level_avg = sum(level_map.get(signal["technical_level"].lower(), 2) for signal in signals) / len(signals)

    return {
        "total_signals": len(signals),
        "critical_count": sum(1 for signal in signals if signal["urgency_score"] >= 8),
        "average_urgency": round(sum(signal["urgency_score"] for signal in signals) / len(signals), 1),
        "sources_active": len(source_counts),
        "most_active_source": source_counts.most_common(1)[0][0],
        "top_use_case": use_case_counts.most_common(1)[0][0],
        "average_developer_level": {1: "Beginner", 2: "Intermediate", 3: "Advanced"}[round(level_avg)],
        "use_case_distribution": [
            {
                "label": label,
                "value": count,
                "percent": round((count / len(signals)) * 100),
            }
            for label, count in use_case_counts.most_common()
        ],
        "source_distribution": [
            {
                "label": label,
                "value": count,
                "percent": round((count / len(signals)) * 100),
            }
            for label, count in source_counts.most_common()
        ],
    }


def session_snapshot(
    signals: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
    outreach: list[dict[str, Any]],
    content: dict[str, Any],
    insights: list[str] | None = None,
) -> dict[str, Any]:
    """Build a compact session object for the frontend and export file."""

    saved_signals = [signal for signal in signals if signal.get("saved")]
    metrics = summary_metrics(signals)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "signals": signals,
        "saved_signals": saved_signals,
        "analyses": analyses,
        "outreach": outreach,
        "content": content,
        "insights": insights or [],
        "metrics": metrics,
    }


def build_session_payload() -> dict[str, Any]:
    """Run the Mem0 GTM pipeline and return a rich dashboard payload."""

    client = make_client()
    pain_points = generate_pain_points(client)
    analyses = enrich_analyses(pain_points, analyze_pain_points(client, pain_points))
    signals = create_signal_records(pain_points, analyses)
    outreach = generate_outreach(client, pain_points, analyses)
    content = generate_content_pieces(client, pain_points, analyses, outreach)
    payload = session_snapshot(signals, analyses, outreach, content)
    return payload


def compact_session_for_prompt(session: dict[str, Any]) -> dict[str, Any]:
    """Reduce a session to the most useful facts for model prompts."""

    return {
        "generated_at": session.get("generated_at"),
        "metrics": session.get("metrics", {}),
        "signals": [
            {
                "source": item.get("source"),
                "title": item.get("title"),
                "use_case": item.get("use_case"),
                "technical_level": item.get("technical_level"),
                "urgency_score": item.get("urgency_score"),
                "urgency_label": item.get("urgency_label"),
                "analysis": item.get("analysis", {}),
            }
            for item in session.get("signals", [])[:5]
        ],
    }


def generate_json(client: Any, prompt: str) -> Any | None:
    """Call Gemini and parse a JSON response if available."""

    raw = call_gemini(client, prompt)
    if not raw:
        return None
    parsed = extract_json(raw)
    return parsed


def fallback_compose(signal: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    """Deterministic outreach variants used when Gemini is unavailable."""

    title = signal.get("title", "this issue")
    pain = analysis.get("what_they_are_struggling_with", "the memory problem")
    tried = analysis.get("what_they_probably_tried", "prompt hacks and embeddings")
    why = analysis.get("why_that_is_failing", "those approaches still leak stale context")
    note = analysis.get("empathy_note", "This is a common production edge case.")
    next_step = analysis.get("likely_next_step", "Separate durable memory from transient chat history.")

    drafts = {
        "helpful": {
            "label": "Helpful",
            "tone_value": 18,
            "text": (
                f"Looks like you're running into the classic memory wall on {title}. {pain}. "
                f"{tried}. {why}. {note} If useful, Mem0 can sit as a memory layer so the app only pulls back the stable facts. "
                f"{next_step}."
            ),
        },
        "technical": {
            "label": "Technical",
            "tone_value": 54,
            "text": (
                f"The tricky part here is not storage, it is retrieval and update policy. {pain}. "
                f"{tried}. {why}. Mem0 handles the memory layer directly, so you do not have to keep rebuilding extraction, dedupe, "
                f"and rehydration logic in your app. {next_step}."
            ),
        },
        "direct": {
            "label": "Direct",
            "tone_value": 82,
            "text": (
                f"You do not need to keep hand-rolling memory for {title}. Mem0 gives you persistent memory for agents in a few lines, "
                f"so you can stop patching prompts and custom retrieval. Happy to share a quick example if that would help."
            ),
        },
    }
    for item in drafts.values():
        item["character_count"] = len(item["text"])
    return drafts


def compose_variants(signal: dict[str, Any], analysis: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generate three outreach variants for a signal."""

    client = make_client()
    prompt = f"""
You are writing outreach for a developer pain point.

Context:
- Signal:
{json.dumps(signal, indent=2)}

- Analysis:
{json.dumps(analysis, indent=2)}

Write 3 drafts in JSON only:
1. helpful: low-pressure, genuine help, pure help tone
2. technical: specific, architecture-aware, practical
3. direct: concise, clear, mention Mem0 once

Each draft should have:
- label
- tone_value (0-100, lower = more help, higher = more direct)
- text

Keep each draft under 750 characters.
"""

    parsed = generate_json(client, prompt)
    if isinstance(parsed, dict) and {"helpful", "technical", "direct"}.issubset(parsed.keys()):
        drafts = parsed
        for key in ("helpful", "technical", "direct"):
            drafts[key]["character_count"] = len(drafts[key].get("text", ""))
            drafts[key]["label"] = drafts[key].get("label", key.title())
        return {"signal_id": signal.get("id"), "drafts": drafts}

    return {"signal_id": signal.get("id"), "drafts": fallback_compose(signal, analysis)}


def fallback_content(angle: str | None, session: dict[str, Any]) -> dict[str, str]:
    """Fallback content generated locally when Gemini is not available."""

    content = session.get("content") or {}
    angle_suffix = f"\n\nAngle: {angle}" if angle else ""
    return {
        "linkedin_post": (content.get("linkedin_post", "") + angle_suffix).strip(),
        "blog_hook": (content.get("blog_hook", "") + angle_suffix).strip(),
        "cold_email": (content.get("cold_email", "") + angle_suffix).strip(),
    }


def regenerate_content(session: dict[str, Any], angle: str | None = None) -> dict[str, Any]:
    """Regenerate the three core content assets, optionally with a target angle."""

    client = make_client()
    prompt = f"""
You are generating GTM content for Mem0.

Target angle:
{angle or "General developer memory pain points"}

Session snapshot:
{json.dumps(compact_session_for_prompt(session), indent=2)}

Return JSON only with these keys:
- linkedin_post
- blog_hook
- cold_email

Tone:
- sharp but human
- specific
- not corporate
- not salesy
"""
    parsed = generate_json(client, prompt)
    if isinstance(parsed, dict) and {"linkedin_post", "blog_hook", "cold_email"}.issubset(parsed.keys()):
        return parsed
    return fallback_content(angle, session)


def generate_strategic_insights(session: dict[str, Any]) -> list[str]:
    """Generate strategic GTM observations from the current session."""

    client = make_client()
    prompt = f"""
You are analyzing a Mem0 GTM session.

Session snapshot:
{json.dumps(compact_session_for_prompt(session), indent=2)}

Write 4 strategic GTM observations as a JSON array of strings.
Focus on:
- source concentration
- urgency patterns
- developer level gaps
- outreach opportunities
"""
    parsed = generate_json(client, prompt)
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed[:4]

    metrics = session.get("metrics", {})
    return [
        f"{metrics.get('most_active_source', 'One source')} produced the highest signal volume in this session.",
        f"Average urgency landed at {metrics.get('average_urgency', 0)}, which suggests the pain is real enough to warrant immediate outreach.",
        f"{metrics.get('top_use_case', 'The top use case')} is the clearest wedge for Mem0 messaging right now.",
        f"{metrics.get('average_developer_level', 'Intermediate')} developers are still the most under-served segment in this session.",
    ]


def build_export_markdown(session: dict[str, Any]) -> str:
    """Render the latest session to a markdown export."""

    lines: list[str] = []
    lines.append("# Mem0 GrowthOS Export")
    lines.append("")
    lines.append(f"Generated: {session.get('generated_at', 'unknown')}")
    lines.append("")

    metrics = session.get("metrics", {})
    lines.append("## Session Metrics")
    lines.append("")
    for key in ("total_signals", "critical_count", "average_urgency", "sources_active", "most_active_source", "top_use_case", "average_developer_level"):
        lines.append(f"- {key.replace('_', ' ').title()}: {metrics.get(key, '')}")
    lines.append("")

    lines.append("## Signals")
    lines.append("")
    for signal in session.get("signals", []):
        lines.append(f"### {signal.get('title')}")
        lines.append(f"- Source: {signal.get('source')}")
        lines.append(f"- Urgency: {signal.get('urgency_score')} ({signal.get('urgency_label')})")
        lines.append(f"- Use case: {signal.get('use_case')}")
        lines.append("")
        lines.append(signal.get("body", ""))
        lines.append("")

    lines.append("## Analyses")
    lines.append("")
    for analysis in session.get("analyses", []):
        lines.append(f"### {analysis.get('title')}")
        lines.append(f"- Struggle: {analysis.get('what_they_are_struggling_with', '')}")
        lines.append(f"- Tried: {analysis.get('what_they_probably_tried', '')}")
        lines.append(f"- Why failing: {analysis.get('why_that_is_failing', '')}")
        lines.append(f"- Next step: {analysis.get('likely_next_step', '')}")
        lines.append("")

    lines.append("## Outreach")
    lines.append("")
    for item in session.get("outreach", []):
        lines.append(f"### {item.get('channel', 'Outreach')}")
        lines.append(item.get("message", ""))
        lines.append("")

    lines.append("## Content")
    lines.append("")
    content = session.get("content", {})
    lines.append("### LinkedIn Post")
    lines.append(content.get("linkedin_post", ""))
    lines.append("")
    lines.append("### Technical Blog Hook")
    lines.append(content.get("blog_hook", ""))
    lines.append("")
    lines.append("### Cold Outreach Email")
    lines.append(content.get("cold_email", ""))
    lines.append("")

    if session.get("insights"):
        lines.append("## Strategic Insights")
        lines.append("")
        for insight in session.get("insights", []):
            lines.append(f"- {insight}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def persist_session(session: dict[str, Any]) -> None:
    """Store the current session and update the export file."""

    global LAST_SESSION_STATE
    LAST_SESSION_STATE = session
    OUTPUT_PATH.write_text(build_export_markdown(session), encoding="utf-8")


def get_session() -> dict[str, Any]:
    """Return the latest session or generate one if none exists."""

    if LAST_SESSION_STATE:
        return LAST_SESSION_STATE
    session = build_session_payload()
    persist_session(session)
    return session


def json_response(payload: dict[str, Any], status: int = 200):
    """Standard JSON response helper."""

    return jsonify(payload), status


def request_json() -> dict[str, Any]:
    """Return request JSON safely."""

    return request.get_json(silent=True) or {}


@app.route("/")
def index():
    """Serve the main dashboard UI."""

    return render_template("index.html")


@app.route("/scan", methods=["POST"])
def scan():
    """Run the full signal discovery pipeline."""

    try:
        session = build_session_payload()
        session["insights"] = generate_strategic_insights(session)
        persist_session(session)
        return json_response(session)
    except Exception as exc:  # pragma: no cover - defensive server-side safety
        traceback.print_exc()
        return json_response({"error": str(exc)}, 500)


@app.route("/run", methods=["POST"])
def run_compat():
    """Compatibility alias for older clients."""

    return scan()


@app.route("/compose", methods=["POST"])
def compose():
    """Generate three outreach variants for a selected signal."""

    try:
        payload = request_json()
        signal = payload.get("signal") or {}
        analysis = payload.get("analysis") or signal.get("analysis") or {}
        session = payload.get("session") or get_session()
        response = compose_variants(signal, analysis, session)
        return json_response(response)
    except Exception as exc:  # pragma: no cover - defensive server-side safety
        traceback.print_exc()
        return json_response({"error": str(exc)}, 500)


@app.route("/regenerate-content", methods=["POST"])
def regenerate_content_route():
    """Regenerate the content command assets, optionally with a focus angle."""

    try:
        payload = request_json()
        session = payload.get("session") or get_session()
        angle = (payload.get("angle") or "").strip() or None
        content = regenerate_content(session, angle)
        session["content"] = content
        if angle:
            session["content_angle"] = angle
        persist_session(session)
        return json_response(content)
    except Exception as exc:  # pragma: no cover - defensive server-side safety
        traceback.print_exc()
        return json_response({"error": str(exc)}, 500)


@app.route("/insights", methods=["POST"])
def insights():
    """Generate strategic observations from the current session data."""

    try:
        payload = request_json()
        session = payload.get("session") or get_session()
        observations = generate_strategic_insights(session)
        session["insights"] = observations
        persist_session(session)
        return json_response({"observations": observations})
    except Exception as exc:  # pragma: no cover - defensive server-side safety
        traceback.print_exc()
        return json_response({"error": str(exc)}, 500)


@app.route("/export")
def export_outputs():
    """Download the latest outputs.md file."""

    session = get_session()
    persist_session(session)
    return send_file(OUTPUT_PATH, as_attachment=True, download_name="outputs.md")


@app.route("/run-stream", methods=["GET", "POST"])
def run_stream_compat():
    """Compatibility SSE endpoint for older clients."""

    session = get_session()
    payload = {
        "status": "complete",
        "message": "Pipeline complete.",
        "session": session,
    }
    return (
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n",
        200,
        {"Content-Type": "text/event-stream", "Cache-Control": "no-cache"},
    )


if __name__ == "__main__":
    port = choose_port()
    print(f"Serving on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
