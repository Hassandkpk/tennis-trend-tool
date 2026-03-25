import streamlit as st
import anthropic

from competitors import (
    EALA_COMPETITOR_CHANNELS,
    ALCARAZ_COMPETITOR_CHANNELS,
    EALA_OWN_CHANNELS,
    ALCARAZ_OWN_CHANNELS,
)
from scanner import get_youtube_client, scan_keyword, scan_competitors
from sheet_writer import append_topic_row, write_test_row

st.set_page_config(page_title="Pipeline Tester", page_icon="🧪", layout="wide")

st.title("🧪 Daily Pipeline Tester")
st.write("Scans outliers, generates viral repeats & outlier remixes, writes all 3 to sheet.")

API_KEY = st.secrets.get("YOUTUBE_API_KEY", None)
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", None)

if not API_KEY:
    st.error("Missing YOUTUBE_API_KEY in Streamlit secrets.")
    st.stop()

if not ANTHROPIC_API_KEY:
    st.error("Missing ANTHROPIC_API_KEY in Streamlit secrets.")
    st.stop()

youtube = get_youtube_client(API_KEY)
claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

PLAYER_CONFIG = {
    "Alex Eala": {
        "keywords": ["Alex Eala"],
        "competitors": EALA_COMPETITOR_CHANNELS,
        "own_channels": EALA_OWN_CHANNELS,
        "sheet_tab": "Topics",
        "player_name": "Alex Eala",
    },
    "Carlos Alcaraz": {
        "keywords": ["Carlos Alcaraz"],
        "competitors": ALCARAZ_COMPETITOR_CHANNELS,
        "own_channels": ALCARAZ_OWN_CHANNELS,
        "sheet_tab": "Alcaraz Topics",
        "player_name": "Carlos Alcaraz",
    },
}


def filter_titles(results):
    filtered = []
    for r in results:
        title = r.get("title", "").lower()
        if any(x in title for x in [" vs ", " vs.", "vs ", " vs"]):
            continue
        filtered.append(r)
    return filtered


def generate_viral_repeat(claude_client, original_title, player_name):
    """
    Takes one of our own viral titles and rewrites it with a fresh angle,
    keeping the same format/structure.
    """
    prompt = f"""You are a YouTube title strategist for a faceless tennis channel about {player_name}.

Here is one of our own viral video titles:
"{original_title}"

Your task: Rewrite this title with a completely FRESH angle and new storyline, but keep the EXACT same format and structure. Same emotional hooks, same title pattern, same length — but a totally new topic/event/angle that hasn't been covered yet.

Rules:
- Output ONLY the new title, nothing else
- No explanations, no preamble, no quotes around the title
- Keep the same structural formula (e.g. if original starts with a name in caps, keep that)
- Make it rage-baity or emotionally charged like the original"""

    message = claude_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def generate_outlier_remix(claude_client, outlier_title, player_name):
    """
    Takes a competitor outlier topic and generates a brand new topic
    inspired by the same angle but not a copy.
    """
    prompt = f"""You are a YouTube title strategist for a faceless tennis channel about {player_name}.

A competitor's video is going viral with this title:
"{outlier_title}"

Your task: Generate a BRAND NEW YouTube title inspired by the same emotional angle and viral hook, but with a completely different storyline, event, or framing. Do NOT copy or rephrase the competitor's title — create something entirely new that captures the same energy.

Rules:
- Output ONLY the new title, nothing else
- No explanations, no preamble, no quotes around the title
- Make it rage-baity, dramatic, or emotionally charged
- It must feel original, not like a remix of the competitor's exact topic"""

    message = claude_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


# ── UI ────────────────────────────────────────────────────────────────────────

selected_player = st.selectbox("Choose topic radar", ["Alex Eala", "Carlos Alcaraz"])
config = PLAYER_CONFIG[selected_player]

KEYWORDS_TO_SCAN = config["keywords"]
COMPETITOR_CHANNELS = config["competitors"]
OWN_CHANNELS = config["own_channels"]
SHEET_NAME = "Tennis Sheet"
SHEET_TAB = config["sheet_tab"]
PLAYER_NAME = config["player_name"]

st.divider()

# ── SECTION 1: Pipeline preview ───────────────────────────────────────────────
st.subheader("🔍 Pipeline Scanner (Preview)")

if st.button("Run Scan Preview"):
    all_results = []

    st.markdown("#### Keyword Results")
    for keyword in KEYWORDS_TO_SCAN:
        keyword_results = scan_keyword(youtube, keyword, max_results=25)
        keyword_results = filter_titles(keyword_results)
        top = keyword_results[:5]
        all_results.extend(top)
        if top:
            st.write(f"Top results for: **{keyword}**")
            st.dataframe(top, use_container_width=True)

    st.markdown("#### Competitor Results")
    competitor_results = scan_competitors(youtube, COMPETITOR_CHANNELS, max_results_per_channel=8)
    competitor_results = filter_titles(competitor_results)
    top_comp = competitor_results[:10]
    all_results.extend(top_comp)
    if top_comp:
        st.dataframe(top_comp, use_container_width=True)

    st.markdown("#### Top Combined (by velocity)")
    all_results = sorted(all_results, key=lambda x: x["velocity"], reverse=True)
    st.dataframe(all_results[:10], use_container_width=True)

st.divider()

# ── SECTION 2: Full pipeline — scan + generate + write ───────────────────────
st.subheader("🚀 Run Full Pipeline → Scan + Generate + Write to Sheet")
st.write("Writes 3 types of topics: **outlier**, **viral_repeat**, **outlier_remix**")

if st.button("Run Full Pipeline"):

    all_written = 0
    today = __import__("datetime").datetime.now().strftime("%Y-%m-%d")

    # ── STEP 1: Collect outliers ──────────────────────────────────────────────
    with st.spinner("Step 1/3 — Scanning for outliers..."):
        raw_results = []

        for keyword in KEYWORDS_TO_SCAN:
            kw_results = scan_keyword(youtube, keyword, max_results=25)
            kw_results = filter_titles(kw_results)
            raw_results.extend(kw_results[:10])

        comp_results = scan_competitors(youtube, COMPETITOR_CHANNELS, max_results_per_channel=8)
        comp_results = filter_titles(comp_results)
        raw_results.extend(comp_results[:15])

        raw_results = sorted(raw_results, key=lambda x: x["velocity"], reverse=True)
        top_outliers = raw_results[:10]

    if top_outliers:
        st.success(f"✅ Found {len(top_outliers)} outliers")
        st.dataframe(top_outliers, use_container_width=True)
    else:
        st.warning("No outliers found.")

    # ── STEP 2: Viral Repeats — our own channels ──────────────────────────────
    with st.spinner(f"Step 2/3 — Fetching your own top videos & generating viral repeats..."):
        own_results = scan_competitors(youtube, OWN_CHANNELS, max_results_per_channel=8)
        own_results = filter_titles(own_results)
        own_results = sorted(own_results, key=lambda x: x["velocity"], reverse=True)
        top_own = own_results[:5]

        viral_repeat_rows = []
        for video in top_own:
            try:
                generated = generate_viral_repeat(claude, video["title"], PLAYER_NAME)
                viral_repeat_rows.append({
                    "date": today,
                    "source": "own_channel",
                    "keyword": "",
                    "player": PLAYER_NAME,
                    "type": "viral_repeat",
                    "title": video["title"],
                    "generated_title": generated,
                    "channel": video["channel"],
                    "views": video["views"],
                    "velocity": video["velocity"],
                    "subscribers": video["subscribers"],
                    "url": video["link"],
                })
            except Exception as e:
                st.warning(f"Claude error on viral repeat: {e}")

    if viral_repeat_rows:
        st.success(f"✅ Generated {len(viral_repeat_rows)} viral repeats")
        st.dataframe(
            [{"original": r["title"], "generated": r["generated_title"]} for r in viral_repeat_rows],
            use_container_width=True
        )

    # ── STEP 3: Outlier Remixes — top 5 outliers → new angles ─────────────────
    with st.spinner("Step 3/3 — Generating outlier remixes with Claude..."):
        outlier_remix_rows = []
        for video in top_outliers[:5]:
            try:
                generated = generate_outlier_remix(claude, video["title"], PLAYER_NAME)
                outlier_remix_rows.append({
                    "date": today,
                    "source": video.get("source_type", "competitor"),
                    "keyword": video.get("keyword", ""),
                    "player": PLAYER_NAME,
                    "type": "outlier_remix",
                    "title": video["title"],
                    "generated_title": generated,
                    "channel": video["channel"],
                    "views": video["views"],
                    "velocity": video["velocity"],
                    "subscribers": video["subscribers"],
                    "url": video["link"],
                })
            except Exception as e:
                st.warning(f"Claude error on outlier remix: {e}")

    if outlier_remix_rows:
        st.success(f"✅ Generated {len(outlier_remix_rows)} outlier remixes")
        st.dataframe(
            [{"source_title": r["title"], "remix": r["generated_title"]} for r in outlier_remix_rows],
            use_container_width=True
        )

    # ── STEP 4: Write everything to sheet ─────────────────────────────────────
    with st.spinner("Writing all topics to Google Sheet..."):

        # Write outliers
        for video in top_outliers:
            append_topic_row(SHEET_NAME, {
                "date": today,
                "source": video.get("source_type", ""),
                "keyword": video.get("keyword", ""),
                "player": PLAYER_NAME,
                "type": "outlier",
                "title": video["title"],
                "generated_title": "",
                "channel": video["channel"],
                "views": video["views"],
                "velocity": video["velocity"],
                "subscribers": video["subscribers"],
                "url": video["link"],
            }, SHEET_TAB)
            all_written += 1

        # Write viral repeats
        for row in viral_repeat_rows:
            append_topic_row(SHEET_NAME, row, SHEET_TAB)
            all_written += 1

        # Write outlier remixes
        for row in outlier_remix_rows:
            append_topic_row(SHEET_NAME, row, SHEET_TAB)
            all_written += 1

    st.success(f"🎉 Done! {all_written} total topics written to **{SHEET_TAB}**")
    st.markdown(f"- **Outliers:** {len(top_outliers)}")
    st.markdown(f"- **Viral Repeats:** {len(viral_repeat_rows)}")
    st.markdown(f"- **Outlier Remixes:** {len(outlier_remix_rows)}")

st.divider()

# ── SECTION 3: Sheet test ─────────────────────────────────────────────────────
st.subheader("🧪 Google Sheets Test")

if st.button("Write Simple Test Row"):
    try:
        write_test_row(SHEET_NAME, SHEET_TAB)
        st.success(f"Test row written to: {SHEET_TAB}")
    except Exception as e:
        st.error(f"Failed to write test row: {e}")
