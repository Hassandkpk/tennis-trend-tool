import streamlit as st
import anthropic
from datetime import datetime

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
    prompt = f"""You are a YouTube title strategist for a faceless tennis channel about {player_name}.

Here is one of our own viral video titles:
"{original_title}"

Your task: Rewrite this title with a completely FRESH angle and new storyline, but keep the EXACT same format and structure. Same emotional hooks, same title pattern, same length — but a totally new topic/event/angle that hasn't been covered yet.

Rules:
- Output ONLY the new title, nothing else
- No explanations, no preamble, no quotes around the title
- Keep the same structural formula
- Make it rage-baity or emotionally charged like the original"""

    message = claude_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()


def generate_outlier_remix(claude_client, outlier_title, player_name):
    prompt = f"""You are a YouTube title strategist for a faceless tennis channel about {player_name}.

A competitor's video is going viral with this title:
"{outlier_title}"

Generate exactly 3 new YouTube title variants. PRESERVE the core emotional hook, the key people/reactions, and the essential structure — do NOT replace the concept. Only update locations or events to be current (e.g. if original says Germany, change to Spain/Madrid since that's where {player_name} is now).

VARIANT 1 — Slightly Stronger: Same title DNA, same structure, same people — just amplify the emotion or stakes slightly. Change as little as possible.

VARIANT 2 — Unique Concept: Keep the same emotional hook and key people, but find a fresh angle or moment that captures the same energy in a new way.

VARIANT 3 — Rage Bait: Same core topic but reframe it as conflict, outrage, or injustice. Add a villain, a betrayal, or an institution being exposed.

Rules:
- Output ONLY the 3 titles, one per line, prefixed exactly as: "1.", "2.", "3."
- No explanations, labels, or extra text
- Keep {player_name} and any reaction figures (e.g. Navratilova, Sabalenka) from the original
- Each title must feel like it belongs to the same viral topic family as the original"""

    message = claude_client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text.strip()
    variants = []
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith(("1.", "2.", "3.")):
            variants.append(line[2:].strip())
    while len(variants) < 3:
        variants.append("")
    return variants[:3]


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

# ── SECTION 1: Preview scan only ─────────────────────────────────────────────
st.subheader("🔍 Preview Scan (no sheet write)")

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

# ── SECTION 2: Full pipeline ──────────────────────────────────────────────────
st.subheader("🚀 Full Pipeline — Scan + Generate + Write to Sheet")
st.write("Produces: **10 outliers** + **1 viral repeat per channel** + **10 outlier remixes**")

if st.button("Run Full Pipeline"):

    all_written = 0
    today = datetime.now().strftime("%Y-%m-%d")
    top_outliers = []
    viral_repeat_rows = []
    outlier_remix_rows = []

    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔴 Step 1 — Outliers")

    try:
        raw_results = []

        for keyword in KEYWORDS_TO_SCAN:
            st.write(f"Scanning keyword: **{keyword}**...")
            kw_results = scan_keyword(youtube, keyword, max_results=25)
            kw_results = filter_titles(kw_results)
            raw_results.extend(kw_results[:10])
            st.write(f"→ {len(kw_results)} keyword results")

        st.write(f"Scanning {len(COMPETITOR_CHANNELS)} competitor channels...")
        comp_results = scan_competitors(youtube, COMPETITOR_CHANNELS, max_results_per_channel=8)
        comp_results = filter_titles(comp_results)
        raw_results.extend(comp_results[:15])
        st.write(f"→ {len(comp_results)} competitor videos")

        raw_results = sorted(raw_results, key=lambda x: x["velocity"], reverse=True)
        top_outliers = raw_results[:10]
        st.success(f"✅ {len(top_outliers)} outliers found")
        st.dataframe(
            [{"title": v["title"], "channel": v["channel"], "views": v["views"], "velocity": v["velocity"]} for v in top_outliers],
            use_container_width=True
        )

    except Exception as e:
        st.error(f"❌ Step 1 failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔵 Step 2 — Viral Repeats (1 per own channel)")

    for channel in OWN_CHANNELS:
        try:
            st.write(f"Fetching videos from **{channel['name']}**...")
            ch_results = scan_competitors(youtube, [channel], max_results_per_channel=50)
            ch_results = filter_titles(ch_results)
            ch_results = sorted(ch_results, key=lambda x: x["views"], reverse=True)

            if not ch_results:
                st.warning(f"⚠️ No videos found for {channel['name']}")
                continue

            top_video = ch_results[0]
            st.write(f"→ Most viewed: **{top_video['title']}** ({top_video['views']:,} views)")

            generated = generate_viral_repeat(claude, top_video["title"], PLAYER_NAME)
            st.write(f"→ New angle: **{generated}**")

            viral_repeat_rows.append({
                "date": today,
                "source": "own_channel",
                "keyword": "",
                "player": PLAYER_NAME,
                "type": "viral_repeat",
                "title": top_video["title"],
                "generated_title": generated,
                "channel": top_video["channel"],
                "views": top_video["views"],
                "velocity": top_video["velocity"],
                "subscribers": top_video["subscribers"],
                "url": top_video["link"],
            })

        except Exception as e:
            st.error(f"❌ Error on {channel['name']}: {e}")

    if viral_repeat_rows:
        st.success(f"✅ {len(viral_repeat_rows)} viral repeats generated")
        st.dataframe(
            [{"channel": r["channel"], "original": r["title"], "new_angle": r["generated_title"]} for r in viral_repeat_rows],
            use_container_width=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🟢 Step 3 — Outlier Remixes (10 new concepts)")

    if not top_outliers:
        st.warning("⚠️ No outliers to remix — Step 1 may have failed.")
    else:
        for video in top_outliers[:10]:
            try:
                st.write(f"Remixing: **{video['title']}**")
                variants = generate_outlier_remix(claude, video["title"], PLAYER_NAME)
                labels = ["Slightly Stronger", "Unique Concept", "Rage Bait"]
                for label, title in zip(labels, variants):
                    st.write(f"→ **{label}:** {title}")
                    outlier_remix_rows.append({
                        "date": today,
                        "source": video.get("source_type", "competitor"),
                        "keyword": video.get("keyword", ""),
                        "player": PLAYER_NAME,
                        "type": f"outlier_remix_{label.lower().replace(' ', '_')}",
                        "title": video["title"],
                        "generated_title": title,
                        "channel": video["channel"],
                        "views": video["views"],
                        "velocity": video["velocity"],
                        "subscribers": video["subscribers"],
                        "url": video["link"],
                    })

            except Exception as e:
                st.error(f"❌ Remix failed for: {video.get('title','?')[:60]} — {e}")

    if outlier_remix_rows:
        st.success(f"✅ {len(outlier_remix_rows)} outlier remixes generated")
        st.dataframe(
            [{"source_title": r["title"], "new_concept": r["generated_title"]} for r in outlier_remix_rows],
            use_container_width=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📝 Step 4 — Writing to Google Sheet")

    for video in top_outliers:
        try:
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
            st.write(f"✅ Outlier: {video['title'][:70]}")
        except Exception as e:
            st.error(f"❌ Outlier write failed: {video.get('title','?')[:60]} — {e}")

    for row in viral_repeat_rows:
        try:
            append_topic_row(SHEET_NAME, row, SHEET_TAB)
            all_written += 1
            st.write(f"✅ Viral repeat: {row['generated_title'][:70]}")
        except Exception as e:
            st.error(f"❌ Viral repeat write failed: {row.get('generated_title','?')[:60]} — {e}")

    for row in outlier_remix_rows:
        try:
            append_topic_row(SHEET_NAME, row, SHEET_TAB)
            all_written += 1
            st.write(f"✅ Outlier remix: {row['generated_title'][:70]}")
        except Exception as e:
            st.error(f"❌ Outlier remix write failed: {row.get('generated_title','?')[:60]} — {e}")

    st.markdown("---")
    st.success(f"🎉 Pipeline complete! **{all_written} topics** written to **{SHEET_TAB}**")
    st.markdown(f"- 🔴 Outliers: **{len(top_outliers)}**")
    st.markdown(f"- 🔵 Viral Repeats: **{len(viral_repeat_rows)}**")
    st.markdown(f"- 🟢 Outlier Remixes: **{len(outlier_remix_rows)}**")

st.divider()


st.divider()

# ── SECTION 3: Sheet debug test ───────────────────────────────────────────────
st.subheader("🧪 Google Sheets Debug Test")

if st.button("Write Simple Test Row"):
    try:
        from sheet_writer import get_gspread_client
        st.write("Step 1: Connecting to Google Sheets...")
        client = get_gspread_client()
        st.write("Step 2: Connected. Opening sheet...")
        sheet = client.open(SHEET_NAME)
        tabs = [ws.title for ws in sheet.worksheets()]
        st.write(f"Step 3: Sheet opened. Tabs found: **{tabs}**")
        worksheet = sheet.worksheet(SHEET_TAB)
        st.write(f"Step 4: Tab **{SHEET_TAB}** found. Writing row...")
        worksheet.append_row(["TEST", "test", "outlier", "TestChannel", "keyword", "TEST TITLE", "", "TestChannel", 999, 24, 10, "https://youtube.com", "", "", "", "", "", ""])
        st.success(f"✅ Row written successfully to **{SHEET_TAB}**! Check your sheet now.")
    except Exception as e:
        st.error(f"❌ FAILED: {e}")
