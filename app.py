import streamlit as st
import pandas as pd
import json
import random
import time
import re
from urllib.parse import urlparse
from dataclasses import dataclass, asdict
from typing import List, Set
from duckduckgo_search import DDGS
# ============================================================
# إعدادات الصفحة
# ============================================================
st.set_page_config(
    page_title="Instagram Public OSINT Searcher",
    page_icon="🔎",
    layout="wide"
)
# ============================================================
# CSS بسيط لتحسين الواجهة
# ============================================================
st.markdown("""
<style>
    .main-title {
        font-size: 38px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .subtitle {
        color: #888;
        font-size: 17px;
        margin-bottom: 25px;
    }
    .result-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)
# ============================================================
# نموذج النتيجة
# ============================================================
@dataclass
class SearchResult:
    username: str
    query: str
    title: str
    url: str
    snippet: str
    domain: str
    source: str
    category: str
    discovered_at: str
# ============================================================
# تنظيف Username
# ============================================================
def normalize_username(username: str) -> str:
    username = username.strip()
    if username.startswith("@"):
        username = username[1:]
    username = re.sub(
        r"[^a-zA-Z0-9._]",
        "",
        username
    )
    return username.lower()
# ============================================================
# التحقق من Username
# ============================================================
def validate_username(username: str) -> bool:
    if not username:
        return False
    if len(username) > 30:
        return False
    return bool(
        re.fullmatch(
            r"[a-zA-Z0-9._]+",
            username
        )
    )
# ============================================================
# توليد استعلامات البحث
# ============================================================
def generate_queries(username: str):
    queries = []
    # --------------------------------------------------------
    # Instagram
    # --------------------------------------------------------
    instagram_queries = [
        f'site:instagram.com "{username}"',
        f'site:instagram.com "@{username}"',
        f'site:instagram.com/p/ "{username}"',
        f'site:instagram.com/reel/ "{username}"',
        f'site:instagram.com/reels/ "{username}"',
        f'site:instagram.com/tv/ "{username}"',
        f'site:instagram.com "{username}" comment',
        f'site:instagram.com "{username}" comments',
        f'site:instagram.com "{username}" mention',
        f'site:instagram.com "{username}" mentioned',
        f'site:instagram.com "@{username}" comment',
        f'site:instagram.com "@{username}" mention',
        f'site:instagram.com "{username}" reel',
        f'site:instagram.com "{username}" post',
    ]
    for q in instagram_queries:
        queries.append({
            "query": q,
            "category": "Instagram"
        })
    # --------------------------------------------------------
    # Threads
    # --------------------------------------------------------
    threads_queries = [
        f'site:threads.net "{username}"',
        f'site:threads.net "@{username}"',
        f'site:threads.net "{username}" Instagram',
        f'site:threads.net "{username}" mention',
        f'site:threads.net "{username}" mentioned',
        f'site:threads.net "@{username}" comment',
    ]
    for q in threads_queries:
        queries.append({
            "query": q,
            "category": "Threads"
        })
    # --------------------------------------------------------
    # Reddit
    # --------------------------------------------------------
    reddit_queries = [
        f'site:reddit.com "{username}" Instagram',
        f'site:reddit.com "@{username}"',
        f'site:reddit.com "{username}" comment',
        f'site:reddit.com "{username}" mention',
        f'site:reddit.com "{username}" reel',
    ]
    for q in reddit_queries:
        queries.append({
            "query": q,
            "category": "Reddit"
        })
    # --------------------------------------------------------
    # Facebook
    # --------------------------------------------------------
    facebook_queries = [
        f'site:facebook.com "{username}" Instagram',
        f'site:facebook.com "@{username}"',
        f'site:facebook.com "{username}" comment',
        f'site:facebook.com "{username}" mention',
    ]
    for q in facebook_queries:
        queries.append({
            "query": q,
            "category": "Facebook"
        })
    # --------------------------------------------------------
    # YouTube
    # --------------------------------------------------------
    youtube_queries = [
        f'site:youtube.com "{username}" Instagram',
        f'site:youtube.com "@{username}"',
        f'site:youtube.com "{username}" comment',
        f'site:youtube.com "{username}" mention',
    ]
    for q in youtube_queries:
        queries.append({
            "query": q,
            "category": "YouTube"
        })
    # --------------------------------------------------------
    # TikTok
    # --------------------------------------------------------
    tiktok_queries = [
        f'site:tiktok.com "{username}" Instagram',
        f'site:tiktok.com "@{username}"',
        f'site:tiktok.com "{username}" mention',
    ]
    for q in tiktok_queries:
        queries.append({
            "query": q,
            "category": "TikTok"
        })
    # --------------------------------------------------------
    # البحث العام
    # --------------------------------------------------------
    generic_queries = [
        f'"{username}" Instagram',
        f'"@{username}" Instagram',
        f'"{username}" Instagram reel',
        f'"{username}" Instagram post',
        f'"{username}" Instagram comment',
        f'"{username}" Instagram comments',
        f'"{username}" Instagram mention',
        f'"@{username}" comment',
        f'"@{username}" mention',
        f'"{username}" social media',
        f'"{username}" profile',
        f'"{username}" creator',
        f'"{username}" influencer',
    ]
    for q in generic_queries:
        queries.append({
            "query": q,
            "category": "General"
        })
    # --------------------------------------------------------
    # الأرشيف
    # --------------------------------------------------------
    archive_queries = [
        f'"{username}" Instagram archive',
        f'"{username}" Instagram archived',
        f'"{username}" Instagram mirror',
        f'"@{username}" archive',
        f'"@{username}" archived',
    ]
    for q in archive_queries:
        queries.append({
            "query": q,
            "category": "Archive"
        })
    # --------------------------------------------------------
    # إزالة التكرار
    # --------------------------------------------------------
    seen = set()
    unique = []
    for item in queries:
        if item["query"] not in seen:
            seen.add(item["query"])
            unique.append(item)
    return unique
# ============================================================
# تصنيف الرابط
# ============================================================
def classify_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        if "instagram.com" in domain:
            if "/reel/" in path:
                return "Instagram Reel"
            if "/reels/" in path:
                return "Instagram Reel"
            if "/p/" in path:
                return "Instagram Post"
            if "/tv/" in path:
                return "Instagram TV"
            if "/stories/" in path:
                return "Instagram Story"
            return "Instagram"
        if "threads.net" in domain:
            return "Threads"
        if "reddit.com" in domain:
            return "Reddit"
        if "facebook.com" in domain:
            return "Facebook"
        if "youtube.com" in domain:
            return "YouTube"
        if "youtu.be" in domain:
            return "YouTube"
        if "tiktok.com" in domain:
            return "TikTok"
        return "Other"
    except Exception:
        return "Unknown"
# ============================================================
# تنفيذ Query واحد
# ============================================================
def search_query(
    query,
    username,
    category,
    max_results
):
    results = []
    try:
        with DDGS() as ddgs:
            search_results = ddgs.text(
                query,
                region="wt-wt",
                safesearch="moderate",
                max_results=max_results
            )
            for item in search_results:
                title = item.get(
                    "title",
                    ""
                ) or ""
                url = item.get(
                    "href",
                    ""
                ) or ""
                snippet = item.get(
                    "body",
                    ""
                ) or ""
                if not url:
                    continue
                domain = urlparse(
                    url
                ).netloc.lower()
                detected_category = classify_url(
                    url
                )
                results.append(
                    SearchResult(
                        username=username,
                        query=query,
                        title=title,
                        url=url,
                        snippet=snippet,
                        domain=domain,
                        source="DuckDuckGo",
                        category=(
                            detected_category
                            if detected_category != "Other"
                            else category
                        ),
                        discovered_at=time.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )
                )
    except Exception as e:
        raise RuntimeError(
            str(e)
        )
    return results
# ============================================================
# إزالة النتائج المكررة
# ============================================================
def deduplicate_results(results):
    seen: Set[str] = set()
    unique = []
    for result in results:
        url = result.url.split("#")[0].strip()
        if url in seen:
            continue
        seen.add(url)
        unique.append(result)
    return unique
# ============================================================
# حساب Score
# ============================================================
def calculate_score(
    result,
    username
):
    score = 0
    text = (
        result.title +
        " " +
        result.snippet +
        " " +
        result.url
    ).lower()
    username = username.lower()
    if f"@{username}" in text:
        score += 10
    if username in text:
        score += 5
    if result.category == "Instagram Reel":
        score += 8
    elif result.category == "Instagram Post":
        score += 7
    elif result.category == "Threads":
        score += 5
    keywords = [
        "comment",
        "comments",
        "mention",
        "mentioned",
        "tag",
        "instagram",
        "reel",
        "post",
    ]
    for keyword in keywords:
        if keyword in text:
            score += 1
    return score
# ============================================================
# تحويل النتائج إلى DataFrame
# ============================================================
def results_to_dataframe(
    results,
    username
):
    rows = []
    for result in results:
        row = asdict(result)
        row["score"] = calculate_score(
            result,
            username
        )
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(
            by="score",
            ascending=False
        )
    return df
# ============================================================
# واجهة التطبيق
# ============================================================
st.markdown(
    '<div class="main-title">🔎 Instagram Public OSINT Searcher</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="subtitle">'
    'البحث في المصادر العامة ومحركات البحث عن إشارات مرتبطة بـ Instagram Username'
    '</div>',
    unsafe_allow_html=True
)
# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    st.header("⚙️ الإعدادات")
    max_results = st.slider(
        "عدد النتائج لكل Query",
        min_value=5,
        max_value=50,
        value=20,
        step=5
    )
    min_delay = st.slider(
        "أقل تأخير بين الاستعلامات",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.5
    )
    max_delay = st.slider(
        "أعلى تأخير بين الاستعلامات",
        min_value=2.0,
        max_value=15.0,
        value=7.0,
        step=0.5
    )
    st.divider()
    st.info(
        "الأداة تبحث في المعلومات العامة المفهرسة "
        "ولا تسجل الدخول إلى Instagram ولا تتجاوز CAPTCHA."
    )
# ============================================================
# Username
# ============================================================
username_input = st.text_input(
    "Instagram Username",
    placeholder="مثال: rrenguk",
    help="اكتب اسم المستخدم فقط بدون الحاجة إلى @"
)
# ============================================================
# زر البحث
# ============================================================
start_search = st.button(
    "🚀 بدء البحث",
    type="primary",
    use_container_width=True
)
# ============================================================
# تنفيذ البحث
# ============================================================
if start_search:
    username = normalize_username(
        username_input
    )
    if not validate_username(username):
        st.error(
            "❌ Username غير صالح."
        )
        st.stop()
    queries = generate_queries(
        username
    )
    st.success(
        f"تم توليد {len(queries)} استعلام بحث."
    )
    progress = st.progress(
        0
    )
    status = st.empty()
    all_results = []
    errors = 0
    for index, query_info in enumerate(
        queries,
        start=1
    ):
        query = query_info["query"]
        category = query_info["category"]
        status.info(
            f"🔍 Query {index}/{len(queries)} — {query}"
        )
        try:
            results = search_query(
                query=query,
                username=username,
                category=category,
                max_results=max_results
            )
            all_results.extend(
                results
            )
        except Exception as e:
            errors += 1
            st.warning(
                f"⚠️ تعذر تنفيذ الاستعلام: {query}\n\n"
                f"{str(e)}"
            )
        progress.progress(
            index / len(queries)
        )
        # ----------------------------------------------------
        # تأخير بين الطلبات
        # ----------------------------------------------------
        if index < len(queries):
            delay = random.uniform(
                min_delay,
                max_delay
            )
            time.sleep(
                delay
            )
    status.success(
        "✅ انتهى البحث."
    )
    # ========================================================
    # إزالة التكرارات
    # ========================================================
    unique_results = deduplicate_results(
        all_results
    )
    df = results_to_dataframe(
        unique_results,
        username
    )
    # ========================================================
    # حفظ النتائج في Session State
    # ========================================================
    st.session_state["results_df"] = df
    st.session_state["username"] = username
    st.session_state["errors"] = errors
# ============================================================
# عرض النتائج
# ============================================================
if "results_df" in st.session_state:
    df = st.session_state[
        "results_df"
    ]
    username = st.session_state[
        "username"
    ]
    errors = st.session_state[
        "errors"
    ]
    st.divider()
    st.subheader(
        f"📊 نتائج البحث عن @{username}"
    )
    # ========================================================
    # الإحصائيات
    # ========================================================
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "إجمالي النتائج",
            len(df)
        )
    with col2:
        instagram_count = len(
            df[
                df["category"].astype(str)
                .str.startswith("Instagram")
            ]
        )
        st.metric(
            "Instagram",
            instagram_count
        )
    with col3:
        threads_count = len(
            df[
                df["category"] == "Threads"
            ]
        )
        st.metric(
            "Threads",
            threads_count
        )
    with col4:
        st.metric(
            "أخطاء البحث",
            errors
        )
    # ========================================================
    # الفلاتر
    # ========================================================
    st.subheader(
        "🔎 فلترة النتائج"
    )
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        categories = [
            "All"
        ] + sorted(
            df["category"]
            .dropna()
            .unique()
            .tolist()
        )
        selected_category = st.selectbox(
            "المصدر",
            categories
        )
    with filter_col2:
        search_text = st.text_input(
            "البحث داخل النتائج",
            placeholder="اكتب كلمة للبحث..."
        )
    filtered_df = df.copy()
    if selected_category != "All":
        filtered_df = filtered_df[
            filtered_df["category"]
            == selected_category
        ]
    if search_text:
        mask = (
            filtered_df["title"]
            .fillna("")
            .str.contains(
                search_text,
                case=False,
                na=False
            )
            |
            filtered_df["snippet"]
            .fillna("")
            .str.contains(
                search_text,
                case=False,
                na=False
            )
            |
            filtered_df["url"]
            .fillna("")
            .str.contains(
                search_text,
                case=False,
                na=False
            )
        )
        filtered_df = filtered_df[
            mask
        ]
    st.write(
        f"عرض {len(filtered_df)} نتيجة"
    )
    # ========================================================
    # عرض الجدول
    # ========================================================
    if not filtered_df.empty:
        display_columns = [
            "score",
            "category",
            "title",
            "url",
            "snippet",
            "domain",
            "query",
            "discovered_at",
        ]
        st.dataframe(
            filtered_df[
                display_columns
            ],
            use_container_width=True,
            column_config={
                "url": st.column_config.LinkColumn(
                    "الرابط"
                ),
                "score": st.column_config.NumberColumn(
                    "Score"
                ),
            },
            hide_index=True
        )
    else:
        st.info(
            "لا توجد نتائج مطابقة للفلاتر الحالية."
        )
    # ========================================================
    # تحميل الملفات
    # ========================================================
    st.divider()
    st.subheader(
        "📥 تحميل النتائج"
    )
    download_col1, download_col2, download_col3 = st.columns(3)
    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------
    json_data = json.dumps(
        filtered_df.to_dict(
            orient="records"
        ),
        ensure_ascii=False,
        indent=2
    )
    with download_col1:
        st.download_button(
            label="📄 تحميل JSON",
            data=json_data,
            file_name=f"{username}_results.json",
            mime="application/json",
            use_container_width=True
        )
    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------
    csv_data = filtered_df.to_csv(
        index=False,
        encoding="utf-8-sig"
    )
    with download_col2:
        st.download_button(
            label="📊 تحميل CSV",
            data=csv_data,
            file_name=f"{username}_results.csv",
            mime="text/csv",
            use_container_width=True
        )
    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------
    import io
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(
        excel_buffer,
        engine="openpyxl"
    ) as writer:
        filtered_df.to_excel(
            writer,
            index=False,
            sheet_name="Results"
        )
    excel_buffer.seek(0)
    with download_col3:
        st.download_button(
            label="📗 تحميل Excel",
            data=excel_buffer,
            file_name=f"{username}_results.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True
        )
# ============================================================
# Footer
# ============================================================
st.divider()
st.caption(
    "Public-source search only • لا يتم تسجيل الدخول إلى الحسابات "
    "أو تجاوز أنظمة الحماية."
)