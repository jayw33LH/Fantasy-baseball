"""
MLB Luck Analyzer — Streamlit app
Run: streamlit run streamlit_app.py
"""

import base64
import json
import os
import re

import streamlit as st
from dotenv import load_dotenv

from luck_analyzer import find_player, get_luck_data

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="⚾ MLB Luck Analyzer",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main .block-container { padding-top: 1.2rem; }
  .luck-header { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.2rem; }
  .subtext { color: #8b949e; font-size: 0.82rem; margin-bottom: 1rem; }
  .demo-banner {
    background: rgba(255,165,0,0.1);
    border: 1px solid rgba(255,165,0,0.4);
    border-radius: 6px;
    padding: 10px 14px;
    color: #ffa500;
    font-size: 0.85rem;
    margin-bottom: 1rem;
  }
  .lucky-score  { color: #3fb950; font-weight: 700; }
  .unlucky-score{ color: #f85149; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def fmt_score(score, is_pitcher=False):
    sign = "+" if score > 0 else ""
    decimals = 2 if is_pitcher else 3
    return f"{sign}{score:.{decimals}f}"


def luck_color(score, threshold=0.015):
    if score > threshold:
        return "🟢"
    if score < -threshold:
        return "🔴"
    return "⚪"


def build_table(players, is_pitcher=False, is_lucky=True, n=25):
    subset = sorted(players, key=lambda p: p["luck_score"], reverse=is_lucky)[:n]
    rows = []
    for i, p in enumerate(subset, 1):
        score = p["luck_score"]
        icon = luck_color(score, threshold=0.20 if is_pitcher else 0.015)
        score_str = fmt_score(score, is_pitcher)

        if is_pitcher:
            era = f"{p['era']:.2f}" if p.get("era") is not None else "—"
            xera = f"{p['xera']:.2f}" if p.get("xera") is not None else (
                f"{p['xwoba']:.3f}" if p.get("xwoba") is not None else "—"
            )
            stat1_label, stat2_label = ("ERA", "xERA") if p.get("era") is not None else ("wOBA", "xwOBA")
            rows.append({
                "#": i,
                "Player": p["name"],
                "PA": int(p["pa"]) if p.get("pa") else "—",
                stat1_label: era,
                stat2_label: xera,
                "Luck": score_str,
                "": icon,
            })
        else:
            woba = f"{p['woba']:.3f}" if p.get("woba") is not None else "—"
            xwoba = f"{p['xwoba']:.3f}" if p.get("xwoba") is not None else "—"
            rows.append({
                "#": i,
                "Player": p["name"],
                "PA": int(p["pa"]) if p.get("pa") else "—",
                "wOBA": woba,
                "xwOBA": xwoba,
                "Luck": score_str,
                "": icon,
            })
    return rows


# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def cached_luck_data():
    return get_luck_data()


# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_refresh = st.columns([8, 1])
with col_title:
    st.markdown('<div class="luck-header">⚾ MLB Luck Analyzer</div>', unsafe_allow_html=True)

with col_refresh:
    if st.button("↻ Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Load data
with st.spinner("Loading Baseball Savant expected stats…"):
    data = cached_luck_data()

batters = data.get("batters", [])
pitchers = data.get("pitchers", [])
ts = data.get("last_updated", "")[:19].replace("T", " ") if data.get("last_updated") else "—"

if data.get("is_demo"):
    st.markdown(
        f'<div class="demo-banner">⚠️ <b>Demo data</b> — {data.get("demo_reason", "")}. '
        "Run this app on your own machine with internet access for live stats.</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="subtext">🔶 Demo data · {len(batters)} batters · {len(pitchers)} pitchers</div>',
        unsafe_allow_html=True,
    )
else:
    src = "📦 Cached" if data.get("cached") else "🟢 Live"
    st.markdown(
        f'<div class="subtext">{src} · Updated {ts} · {len(batters)} batters · {len(pitchers)} pitchers</div>',
        unsafe_allow_html=True,
    )

if data.get("error"):
    st.error(f"Data error: {data['error']}")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_bat, tab_pit, tab_search, tab_screenshot = st.tabs(
    ["🏏 Batters", "⚾ Pitchers", "🔍 Search Player", "📸 Screenshot Analyzer"]
)

# ── BATTERS TAB ───────────────────────────────────────────────────────────────
with tab_bat:
    st.info(
        "**Batter luck = wOBA − xwOBA.** "
        "🟢 **Positive (lucky)** → getting more than contact quality deserves — *expect regression, sell high*. "
        "🔴 **Negative (unlucky)** → deserves better results — *expect improvement, buy low*. Min 100 PA."
    )
    col_lucky, col_unlucky = st.columns(2)

    with col_lucky:
        st.markdown("### 🍀 Luckiest Batters — Sell High")
        rows = build_table(batters, is_pitcher=False, is_lucky=True)
        import pandas as pd
        st.dataframe(
            pd.DataFrame(rows).set_index("#"),
            use_container_width=True,
            height=700,
        )

    with col_unlucky:
        st.markdown("### 💀 Unluckiest Batters — Buy Low")
        rows = build_table(batters, is_pitcher=False, is_lucky=False)
        st.dataframe(
            pd.DataFrame(rows).set_index("#"),
            use_container_width=True,
            height=700,
        )

# ── PITCHERS TAB ─────────────────────────────────────────────────────────────
with tab_pit:
    st.info(
        "**Pitcher luck = xERA − ERA.** "
        "🟢 **Positive (lucky)** → ERA lower than underlying quality — *expect regression, fade/sell*. "
        "🔴 **Negative (unlucky)** → ERA higher than deserved — *expect improvement, stream/buy*. Min 100 BF."
    )
    col_lucky, col_unlucky = st.columns(2)

    with col_lucky:
        st.markdown("### 🍀 Luckiest Pitchers — Fade / Sell")
        rows = build_table(pitchers, is_pitcher=True, is_lucky=True)
        st.dataframe(
            pd.DataFrame(rows).set_index("#"),
            use_container_width=True,
            height=700,
        )

    with col_unlucky:
        st.markdown("### 💀 Unluckiest Pitchers — Stream / Buy")
        rows = build_table(pitchers, is_pitcher=True, is_lucky=False)
        st.dataframe(
            pd.DataFrame(rows).set_index("#"),
            use_container_width=True,
            height=700,
        )

# ── SEARCH TAB ────────────────────────────────────────────────────────────────
with tab_search:
    st.markdown("### Search any MLB player for their luck profile")
    query = st.text_input("Player name", placeholder="e.g. Aaron Judge, Shohei Ohtani, Zack Wheeler…")
    ptype = st.radio("Filter", ["All", "Batters only", "Pitchers only"], horizontal=True)

    if query and len(query) >= 2:
        q = query.lower()
        results = []
        if ptype != "Pitchers only":
            results += [dict(p, _type="batter") for p in batters if q in p["name"].lower()]
        if ptype != "Batters only":
            results += [dict(p, _type="pitcher") for p in pitchers if q in p["name"].lower()]

        # Dedupe
        seen = set()
        deduped = []
        for p in results:
            if p["name"] not in seen:
                seen.add(p["name"])
                deduped.append(p)

        if not deduped:
            st.warning("No players found. Try a last name or partial name.")
        else:
            for p in deduped[:10]:
                score = p["luck_score"]
                is_pitcher = p["_type"] == "pitcher"
                threshold = 0.25 if is_pitcher else 0.015
                if score > threshold:
                    status = "🟢 Lucky — consider selling high / fading"
                    color = "green"
                elif score < -threshold:
                    status = "🔴 Unlucky — consider buying low / streaming"
                    color = "red"
                else:
                    status = "⚪ Neutral — close to expected performance"
                    color = "gray"

                with st.expander(f"{p['name']}  ({p['_type']})  {fmt_score(score, is_pitcher)}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    if is_pitcher:
                        c1.metric("ERA", f"{p['era']:.2f}" if p.get("era") else "—")
                        c2.metric("xERA", f"{p['xera']:.2f}" if p.get("xera") else "—")
                    else:
                        c1.metric("wOBA", f"{p['woba']:.3f}" if p.get("woba") else "—")
                        c2.metric("xwOBA", f"{p['xwoba']:.3f}" if p.get("xwoba") else "—")
                    c3.metric("Luck Score", fmt_score(score, is_pitcher))
                    st.markdown(f"**{status}**")


# ── SCREENSHOT ANALYZER TAB ───────────────────────────────────────────────────
with tab_screenshot:
    st.markdown("### 📸 Fantasy Roster Screenshot Analyzer")
    st.markdown(
        "Upload a screenshot of your **fantasy roster**, **free agents**, or **opponent's roster** — "
        "Claude reads the player names and tells you who's lucky or unlucky right now."
    )

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-…  (get one free at console.anthropic.com)",
            help="Your key is used only for this session and never stored.",
        )

    context = st.selectbox(
        "This screenshot is…",
        [
            "my fantasy roster",
            "available free agents in my fantasy league",
            "an opponent's fantasy roster",
            "players I'm considering trading for",
            "players I'm considering dropping",
        ],
    )

    uploaded = st.file_uploader(
        "Upload screenshot",
        type=["png", "jpg", "jpeg", "webp", "gif"],
        label_visibility="collapsed",
    )

    if uploaded:
        st.image(uploaded, caption="Uploaded screenshot", use_column_width=True)

    if st.button("🔍 Analyze Screenshot", type="primary", disabled=not uploaded or not api_key):
        if not api_key:
            st.error("Please enter your Anthropic API key above.")
        elif not uploaded:
            st.warning("Please upload a screenshot first.")
        else:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            img_bytes = uploaded.read()
            img_b64 = base64.standard_b64encode(img_bytes).decode()
            media_type = uploaded.type or "image/png"
            if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                media_type = "image/png"

            with st.spinner("Reading player names from screenshot…"):
                extract = client.messages.create(
                    model="claude-opus-4-8",
                    max_tokens=800,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": img_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    f"This is a screenshot of {context} from a fantasy baseball app.\n\n"
                                    "Extract ALL MLB player names visible. Return ONLY a JSON array, e.g.: "
                                    '[\"Mike Trout\", \"Shohei Ohtani\"]\n\nReturn only the JSON array.'
                                ),
                            },
                        ],
                    }],
                )

            raw = extract.content[0].text.strip()
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            try:
                player_names = json.loads(match.group()) if match else []
            except Exception:
                player_names = []

            if not player_names:
                st.error(f"Could not identify player names. Raw response: {raw}")
                st.stop()

            st.success(f"Found {len(player_names)} players: {', '.join(player_names)}")

            # Cross-reference with luck data
            matched = []
            for name in player_names:
                b = find_player(name, batters)
                p = find_player(name, pitchers)
                hit = b or p
                ptype_found = "batter" if b else ("pitcher" if p else "unknown")
                if hit:
                    score = hit["luck_score"]
                    thresh = 0.015 if ptype_found == "batter" else 0.25
                    matched.append({
                        "name": name,
                        "matched_name": hit["name"],
                        "type": ptype_found,
                        "luck_score": score,
                        "lucky": score > thresh,
                        "unlucky": score < -thresh,
                        "stats": hit,
                    })
                else:
                    matched.append({
                        "name": name,
                        "matched_name": None,
                        "type": "unknown",
                        "luck_score": None,
                        "stats": None,
                    })

            # Show player cards
            st.markdown("#### Player Luck Breakdown")
            cols = st.columns(min(len(matched), 4))
            for i, p in enumerate(matched):
                with cols[i % 4]:
                    if p["stats"]:
                        score = p["luck_score"]
                        is_pit = p["type"] == "pitcher"
                        icon = "🟢" if p["lucky"] else ("🔴" if p["unlucky"] else "⚪")
                        label = "Lucky" if p["lucky"] else ("Unlucky" if p["unlucky"] else "Neutral"  )
                        st.metric(
                            label=f"{icon} {p['name']}",
                            value=fmt_score(score, is_pit),
                            delta=f"{label} {p['type']}",
                            delta_color="normal" if p["lucky"] else ("inverse" if p["unlucky"] else "off"),
                        )
                    else:
                        st.metric(label=p["name"], value="—", delta="not in dataset", delta_color="off")

            # AI analysis
            with st.spinner("Generating fantasy analysis…"):
                analysis_resp = client.messages.create(
                    model="claude-opus-4-8",
                    max_tokens=2000,
                    messages=[{
                        "role": "user",
                        "content": (
                            "You are a fantasy baseball analyst specializing in sabermetric luck analysis.\n\n"
                            f"Context: {context}\n\n"
                            "Player luck data:\n" + json.dumps(matched, indent=2) + "\n\n"
                            "Luck score guide:\n"
                            "• Batters: luck = wOBA − xwOBA. Positive = lucky (more than deserved, expect regression). "
                            "Negative = unlucky (less than deserved, expect improvement).\n"
                            "• Pitchers: luck = xERA − ERA. Positive = lucky (ERA better than underlying quality). "
                            "Negative = unlucky (ERA worse than deserved).\n\n"
                            "Provide:\n"
                            "1. **SELL HIGH / FADE** — lucky players to move\n"
                            "2. **BUY LOW / TARGET** — unlucky players to acquire\n"
                            "3. **Specific actions** — start/sit, add/drop, trade advice\n\n"
                            "Be concise, direct, and actionable. Use bullet points."
                        ),
                    }],
                )

            st.markdown("#### 🤖 AI Fantasy Analysis")
            st.markdown(analysis_resp.content[0].text)
