import streamlit as st
import time
import re
import os
from collections import deque

# ---- set_page_config MUST be first ----
st.set_page_config(page_title="Scenario Planner", page_icon="🗺️", layout="wide")

# ---- Theme ----
from neonui import apply_theme
apply_theme("cosmic_purple")

# ---- Gemma 4 client (reads key from environment) ----
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemma_client = None
gemma_ready = False

if GEMINI_API_KEY:
    try:
        from google import genai
        gemma_client = genai.Client(api_key=GEMINI_API_KEY)
        gemma_ready = True
    except Exception:
        gemma_ready = False

st.title("🗺️ Scenario Planner")
st.write("*Type a scenario. See its parts. Change one thing. Watch the ripple.*")
st.divider()

# ============================================================
# COMPONENTS
# ============================================================
def make_components(items):
    out = []
    seen = set()
    for item in items:
        if isinstance(item, tuple):
            name, desc = item
        else:
            name, desc = item, f"Key area: {item}"
        base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        cid = base
        n = 2
        while cid in seen:
            cid = f"{base}_{n}"
            n += 1
        seen.add(cid)
        out.append({
            "id": cid,
            "name": name,
            "description": desc,
            "category": "general",
        })
    return out

# ============================================================
# TEMPLATES
# ============================================================
TEMPLATES = {
    "college fest": {
        "label": "College Fest",
        "components": make_components([
            ("Planning & Budget", "Overall coordination and money allocation."),
            ("Venue", "Physical space, setup, and supplies."),
            ("Events", "The actual programmes and performances."),
            ("Marketing", "Promotion, social media, and publicity."),
            ("Sponsors", "External funding and financial deals."),
            ("Volunteers", "Team members running the fest."),
            ("Safety", "Legal clearances and crowd safety."),
            ("Attendee Experience", "What visitors actually feel and remember."),
        ]),
        "links": [("Sponsors", "Planning & Budget"),
                  ("Planning & Budget", "Venue"),
                  ("Planning & Budget", "Events"),
                  ("Volunteers", "Events"),
                  ("Volunteers", "Venue"),
                  ("Marketing", "Attendee Experience"),
                  ("Venue", "Attendee Experience"),
                  ("Events", "Attendee Experience"),
                  ("Safety", "Attendee Experience")],
    },
    "wedding": {
        "label": "Wedding",
        "components": make_components([
            ("Budget", "Total spend and how it's allocated."),
            ("Venue", "Location, seating, and decoration."),
            ("Catering", "Food, drinks, and service."),
            ("Guests", "Who comes and how they're invited."),
            ("Outfits", "Bride, groom, and family attire."),
            ("Ceremony", "Religious and cultural programme."),
            ("Photography", "Capturing the day."),
            ("Logistics", "Travel, stay, and coordination."),
        ]),
        "links": [("Budget", "Venue"), ("Budget", "Catering"),
                  ("Guests", "Catering"), ("Guests", "Venue"),
                  ("Venue", "Ceremony"), ("Ceremony", "Photography"),
                  ("Outfits", "Photography"), ("Logistics", "Guests")],
    },
    "hackathon": {
        "label": "Hackathon",
        "components": make_components([
            ("Budget", "Prize money, food, and venue costs."),
            ("Theme", "What participants will build."),
            ("Judges", "Experts evaluating and guiding."),
            ("Participants", "The builders and their teams."),
            ("Venue", "Space, power, and connectivity."),
            ("Sponsors", "Backers and rewards."),
            ("Schedule", "Timeline and rounds."),
            ("Submission", "How projects are handed in and shown."),
        ]),
        "links": [("Sponsors", "Budget"), ("Budget", "Venue"),
                  ("Theme", "Participants"), ("Venue", "Participants"),
                  ("Sponsors", "Judges"), ("Participants", "Submission"),
                  ("Schedule", "Submission"), ("Judges", "Submission")],
    },
    "startup": {
        "label": "Startup Launch",
        "components": make_components([
            ("Idea", "The core product or service concept."),
            ("Team", "Founders and early hires."),
            ("Funding", "Capital to build and grow."),
            ("Product", "What you're actually shipping."),
            ("Marketing", "Getting the word out."),
            ("Customers", "Who pays for it."),
            ("Legal", "Incorporation, contracts, compliance."),
            ("Growth", "Scaling after launch."),
        ]),
        "links": [("Idea", "Product"), ("Team", "Product"),
                  ("Funding", "Team"), ("Product", "Customers"),
                  ("Marketing", "Customers"), ("Legal", "Product"),
                  ("Customers", "Growth"), ("Growth", "Funding")],
    },
    "exam": {
        "label": "Exam Preparation",
        "components": make_components([
            ("Syllabus", "What needs to be covered."),
            ("Study Plan", "Schedule and milestones."),
            ("Materials", "Books, notes, resources."),
            ("Practice", "Solving problems."),
            ("Revision", "Going back over weak areas."),
            ("Health", "Sleep, food, exercise."),
            ("Time", "Hours available each day."),
            ("Mock Tests", "Simulated exam conditions."),
        ]),
        "links": [("Syllabus", "Study Plan"), ("Study Plan", "Materials"),
                  ("Materials", "Practice"), ("Practice", "Mock Tests"),
                  ("Mock Tests", "Revision"), ("Health", "Study Plan"),
                  ("Time", "Study Plan"), ("Revision", "Mock Tests")],
    },
}

GENERIC = {
    "label": "Generic Plan",
    "components": make_components([
        ("Goal", "What success looks like."),
        ("People", "Who is involved and what they do."),
        ("Resources", "Money, tools, and materials."),
        ("Plan", "The sequence of steps."),
        ("Risks", "What could go wrong."),
        ("Execution", "Doing the work."),
        ("Communication", "Keeping everyone aligned."),
        ("Outcome", "Results and lessons learned."),
    ]),
    "links": [("Goal", "Plan"), ("Goal", "People"),
              ("Resources", "Plan"), ("Plan", "Execution"),
              ("People", "Execution"), ("Risks", "Plan"),
              ("Execution", "Outcome"), ("Communication", "Execution")],
}

KEYWORDS = {
    "college fest": ["college fest", "college festival", "campus fest", "fest"],
    "wedding": ["wedding", "marriage", "shaadi"],
    "hackathon": ["hackathon", "hack fest", "coding competition"],
    "startup": ["startup", "start up", "new company", "launch"],
    "exam": ["exam", "examination", "study", "test prep"],
}

# ============================================================
# GEMMA 4 — scenario matching
# ============================================================
def match_with_gemma(text):
    """Ask Gemma 4 which template fits. Returns template key or None."""
    if not gemma_ready:
        return None
    try:
        prompt = (
            f'Classify this scenario into ONE of these categories: '
            f'college fest, wedding, hackathon, startup, exam, generic.\n\n'
            f'Scenario: "{text}"\n\n'
            f'Reply with ONLY the category name, lowercase, nothing else.'
        )
        response = gemma_client.models.generate_content(
            model="gemma-3-27b-it",
            contents=prompt,
        )
        result = response.text.strip().lower()
        result = re.sub(r"[^a-z ]", "", result).strip()
        for key in TEMPLATES:
            if key in result:
                return key
        return None
    except Exception:
        return None

# ============================================================
# KEYWORD FALLBACK
# ============================================================
def match_with_keywords(text):
    text = " ".join(text.lower().strip().split())
    if not text:
        return None
    best_key, best_score = None, 0
    for key, words in KEYWORDS.items():
        for word in words:
            pattern = r"\b" + re.escape(word) + r"\b"
            if re.search(pattern, text) and len(word) > best_score:
                best_score = len(word)
                best_key = key
    return best_key

def match_scenario(text):
    """Returns (template, is_known, source)."""
    if not text.strip():
        return None, False, "none"

    key = match_with_gemma(text)
    source = "gemma"

    if not key:
        key = match_with_keywords(text)
        source = "keywords"

    if key:
        return TEMPLATES[key], True, source

    return GENERIC, False, "fallback"

# ============================================================
# IMPACT
# ============================================================
def find_direct_affected(change, components):
    c = change.lower()
    names = [comp["name"] for comp in components]
    matches = []

    rules = {
        "budget":   ["budget", "resources", "funding", "finance", "sponsor"],
        "money":    ["budget", "resources", "funding", "finance", "sponsor"],
        "cut":      ["budget", "resources", "funding"],
        "cost":     ["budget", "resources", "funding"],
        "speaker":  ["event", "marketing", "attendee", "ceremony"],
        "cancel":   ["event", "marketing", "schedule"],
        "volunteer":["volunteer", "people", "team", "staff"],
        "people":   ["volunteer", "people", "team", "staff"],
        "venue":    ["venue", "location", "logistics"],
        "unavailable": ["venue", "location", "schedule"],
        "time":     ["schedule", "time", "plan"],
        "delay":    ["schedule", "time", "plan"],
        "sick":     ["health", "people", "team"],
        "sponsor":  ["sponsor", "funding", "budget"],
        "lost":     ["volunteer", "people", "sponsor"],
    }

    for trigger, targets in rules.items():
        pattern = r"\b" + re.escape(trigger) + r"\b"
        if re.search(pattern, c):
            for name in names:
                if any(t in name.lower() for t in targets):
                    if name not in matches:
                        matches.append(name)

    if not matches:
        matches = names[:3]

    return matches

def trace_ripple(direct_affected, links):
    graph = {}
    for src, dst in links:
        graph.setdefault(src, []).append(dst)

    visited = set(direct_affected)
    queue = deque(direct_affected)

    while queue:
        current = queue.popleft()
        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited

def find_affected(change, components, links):
    direct = find_direct_affected(change, components)
    all_affected = list(trace_ripple(direct, links))
    order = [c["name"] for c in components]
    all_affected.sort(key=lambda x: order.index(x) if x in order else 999)
    return direct, all_affected

# ============================================================
# GRAPH
# ============================================================
def render_graph(components, links, affected=None):
    affected = affected or []
    try:
        from graphviz import Digraph
    except ImportError:
        st.warning("Install `graphviz` to see the visual graph. Showing text version.")
        for src, dst in links:
            st.write(f"**{src}** ➜ {dst}")
        return

    dot = Digraph()
    dot.attr(rankdir="LR", bgcolor="transparent", pad="0.5")
    dot.attr("node", shape="box", style="rounded,filled",
             fontname="Helvetica", fontsize="11")
    dot.attr("edge", color="#8b5cf6", arrowsize="0.7")

    for comp in components:
        name = comp["name"]
        if name in affected:
            dot.node(name, name, fillcolor="#fee2e2", color="#ef4444")
        else:
            dot.node(name, name, fillcolor="#ede9fe", color="#8b5cf6")

    for src, dst in links:
        dot.edge(src, dst)

    try:
        st.graphviz_chart(dot)
    except Exception:
        st.warning("Graph rendering unavailable — showing text version.")
        for src, dst in links:
            st.write(f"**{src}** ➜ {dst}")

# ============================================================
# SESSION STATE
# ============================================================
for key, default in [
    ("scenario_input", ""),
    ("result", None),
    ("trigger_build", False),
    ("component_data", {}),
    ("change_input", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default

def set_scenario(value):
    st.session_state.scenario_input = value
    st.session_state.trigger_build = True
    st.session_state.change_input = ""

# ============================================================
# AI STATUS BADGE
# ============================================================
if gemma_ready:
    st.success("🤖 Gemma 4 connected — scenario matching is AI-powered")
else:
    st.info("ℹ️ Running in rule-based mode. Set `GEMINI_API_KEY` to enable Gemma 4.")

# ============================================================
# INPUT
# ============================================================
st.subheader("1️⃣ Describe your scenario")

col_a, col_b = st.columns([3, 1])
with col_a:
    scenario = st.text_input(
        "Scenario",
        key="scenario_input",
        placeholder="e.g. college fest, wedding, hackathon, startup, exam",
        label_visibility="collapsed",
    )
with col_b:
    build = st.button("🗺️ Build Map", type="primary", use_container_width=True)

st.caption("Quick examples:")
chip_cols = st.columns(5)
examples = ["college fest", "wedding", "hackathon", "startup", "exam"]
for i, ex in enumerate(examples):
    with chip_cols[i]:
        st.button(
            ex.title(),
            use_container_width=True,
            key=f"chip_{i}",
            on_click=set_scenario,
            args=(ex,),
        )

# ============================================================
# BUILD
# ============================================================
if build and not scenario.strip():
    st.warning("Please enter a scenario first.")
elif (build or st.session_state.trigger_build) and scenario.strip():
    with st.spinner("Understanding your scenario..."):
        template, is_known, source = match_scenario(scenario)
    st.session_state.result = {
        "input": scenario.strip(),
        "template": template,
        "is_known": is_known,
        "source": source,
        "change": None,
        "direct": None,
        "affected": None,
    }
    st.session_state.trigger_build = False

# ============================================================
# DISPLAY
# ============================================================
if st.session_state.result:
    r = st.session_state.result
    t = r["template"]

    st.divider()
    st.subheader(f"2️⃣ Map: {t['label']}")

    source_labels = {
        "gemma":    "🤖 Matched by Gemma 4",
        "keywords": "🔍 Matched by keywords",
        "fallback": "🔧 Generic fallback",
        "none":     "—",
    }
    st.caption(f"Input: *{r['input']}*  •  {source_labels.get(r['source'], '—')}")

    st.markdown("### 🕸️ Dependency Map")
    st.caption("Arrow = source influences target. Red = impacted after change.")
    render_graph(t["components"], t["links"], affected=r.get("affected") or [])

    st.markdown("### 🧩 Components")
    st.caption("Add owners, set status, and jot notes — it persists during the session.")

    cols = st.columns(2)
    for i, comp in enumerate(t["components"]):
        name = comp["name"]
        with cols[i % 2]:
            with st.container(border=True):
                st.markdown(f"**{name}**")
                st.caption(comp["description"])

                saved = st.session_state.component_data.get(name, {})

                status_options = ["Not started", "In progress", "Done", "At risk"]
                current_status = saved.get("status", "Not started")
                if current_status not in status_options:
                    current_status = "Not started"

                status = st.selectbox(
                    "Status",
                    status_options,
                    index=status_options.index(current_status),
                    key=f"status_{comp['id']}",
                )
                owner = st.text_input(
                    "Owner",
                    value=saved.get("owner", ""),
                    placeholder="Name",
                    key=f"owner_{comp['id']}",
                )
                notes = st.text_area(
                    "Notes",
                    value=saved.get("notes", ""),
                    placeholder="Blockers, ideas, details...",
                    key=f"notes_{comp['id']}",
                    height=70,
                )

                st.session_state.component_data[name] = {
                    "status": status,
                    "owner": owner,
                    "notes": notes,
                }

    with st.expander("📋 Full dependency list"):
        for src, dst in t["links"]:
            st.write(f"**{src}** ➜ {dst}")

    # ============================================================
    # CHANGE
    # ============================================================
    st.divider()
    st.subheader("3️⃣ Change one thing")

    change = st.text_input(
        "What changed?",
        key="change_input",
        placeholder="e.g. budget cut by 50%, main speaker cancelled",
        label_visibility="collapsed",
    )

    if st.button("⚡ Simulate Change", type="primary", use_container_width=True):
        if not change.strip():
            st.warning("Type a change first.")
        else:
            with st.spinner("Tracing the ripple through dependencies..."):
                time.sleep(0.5)
            direct, affected = find_affected(
                change, t["components"], t["links"]
            )
            st.session_state.result["change"] = change.strip()
            st.session_state.result["direct"] = direct
            st.session_state.result["affected"] = affected
            st.rerun()

    # ============================================================
    # RIPPLE
    # ============================================================
    if r.get("change") and r.get("affected"):
        st.divider()
        st.subheader(f"4️⃣ After: *{r['change']}*")

        direct = r.get("direct") or []
        affected = r["affected"]
        safe = [c["name"] for c in t["components"] if c["name"] not in affected]

        col1, col2 = st.columns(2)
        with col1:
            st.error("❌ **Broke**")
            for a in affected:
                marker = "🔴 directly" if a in direct else "🟠 because of ripple"
                st.write(f"- {a}  *({marker})*")
        with col2:
            st.success("✅ **Still Fine**")
            for s in safe:
                st.write(f"- {s}")

        st.markdown("### 🌊 How It Spreads")
        st.caption("Follows real connections in the map.")

        for d in direct:
            downstream = trace_ripple([d], t["links"]) - {d}
            st.write(f"**{d}** broke first")
            for comp in t["components"]:
                if comp["name"] in downstream:
                    st.write(f"　↳ then **{comp['name']}** broke")

        # Simplified recovery plan
        st.markdown("### 🛠️ What to do now")

        direct_list = ", ".join(direct) if direct else "the broken parts"
        affected_count = len(affected)

        st.info(
            f"**{affected_count} part(s) broke. Here's your plan:**\n\n"
            f"**1. Fix the broken parts first**\n"
            f"Start with: *{direct_list}*\n\n"
            f"**2. Move help from the safe parts**\n"
            f"Take people, money, or time from parts that are still okay.\n\n"
            f"**3. Use cheaper options**\n"
            f"Can't afford it? Find a smaller, free, or DIY version.\n\n"
            f"**4. Tell everyone early**\n"
            f"Don't wait. Let the team and guests know what changed."
        )

else:
    st.info("👆 Type a scenario above (or click an example) and hit **Build Map**.")
