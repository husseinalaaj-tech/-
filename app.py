import streamlit as st
import requests
import urllib.parse
import json
import io
import csv
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

# ---------------------------------------------------------
# 1. إعدادات الصفحة والواجهة العامة
# ---------------------------------------------------------
st.set_page_config(
    page_title="Instagram OSINT Multi-Engine Search Extractor",
    page_icon="📸",
    layout="wide"
)

st.markdown("""
<style>
    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] li,
    h1, h2, h3, h4 {
        direction: rtl;
        text-align: right;
    }
    .stTextInput input, .stTextArea textarea {
        direction: rtl;
        text-align: right;
    }
    div[data-testid="stCaptionContainer"] {
        direction: rtl;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

st.title("📸 أداة البحث المجمع عن حسابات انستغرام (OSINT Extract)")
st.markdown(
    "تطبيق مخصص لتوليد صيغ البحث المتقدمة (Google Dorks) واستعلام محركات البحث والأرشيفات "
    "للعثور على الحسابات والصفحات المؤرشفة والمرتبطة بيوزر انستغرام معين."
)

with st.expander("ℹ️ طريقة الاستخدام (اضغط للفتح)", expanded=False):
    st.markdown("""
1. **في خانة البحث بالأسفل**: أدخل **يوزر انستغرام** المطلوبة (مثال: `username` أو بدون @).
2. **من القائمة الجانبية**: فعّل المحركات التي ترغب بالبحث عبرها وأدخل مفاتيح API الخاصة بك (إن وجدت).
3. **آلية العمل**: ستقوم الأداة تلقائياً بإنشاء وتنفيذ صيغ ذكية عبر مشغلات البحث والأرشيفات.
4. بعد الانتهاء، يمكنك **ترتيب وتصفية** النتائج وتصديرها كـ JSON أو CSV.
    """)

st.divider()

# ---------------------------------------------------------
# 2. القائمة الجانبية: الإعدادات العامة + إدارة مفاتيح API
# ---------------------------------------------------------
ENGINE_BADGES = {
    "Google": "🟦",
    "Bing": "🟪",
    "Brave": "🦁",
    "DuckDuckGo": "🦆",
    "SearxNG": "🔎",
    "Wayback Archive": "🗄️",
}
ALL_ENGINE_NAMES = list(ENGINE_BADGES.keys())

st.sidebar.header("⚙️ إعدادات البحث المتقدم")
num_results = st.sidebar.slider("عدد النتائج المطلوبة من كل صيغة/محرك", min_value=3, max_value=20, value=10, step=1)

st.sidebar.divider()
st.sidebar.header("🆓 محركات لا تحتاج مفتاح API")

with st.sidebar.expander("🦆 DuckDuckGo", expanded=False):
    st.caption("بحث نصي فعلي داخل الصفحات، عبر النسخة الثابتة من الموقع.")

with st.sidebar.expander("🔎 SearxNG (محرك بحث تجميعي مجاني)", expanded=False):
    searx_instance = st.text_input(
        "رابط خادم SearxNG (Instance URL)",
        value="https://searx.be",
        help="إن لم تظهر نتائج، جرّب رابط خادم SearxNG عام آخر."
    )

with st.sidebar.expander("🗄️ Wayback Machine (أرشيف الإنترنت)", expanded=False):
    st.caption("يبحث في الروابط والصفحات المؤرشفة القديمة لحساب انستغرام المستهدف.")

st.sidebar.divider()
st.sidebar.header("🔑 محركات تتطلب مفتاح API")

with st.sidebar.expander("🟦 Google Custom Search", expanded=False):
    google_api_key = st.text_input("Google API Key", type="password", key="google_api_key")
    google_cx_id = st.text_input("Google Custom Search (CX ID)", type="password", key="google_cx_id")

with st.sidebar.expander("🦁 Brave Search API", expanded=False):
    brave_api_key = st.text_input("Brave Search API Key", type="password", key="brave_api_key")

with st.sidebar.expander("🟪 Bing Search API (متوقفة ⚠️)", expanded=False):
    bing_api_key = st.text_input("Bing Search API Key", type="password", key="bing_api_key")
    st.warning("أوقفت مايكروسوفت خدمة Bing Search API نهائياً في أغسطس 2025.")

st.sidebar.divider()
enabled_engines = st.sidebar.multiselect(
    "✅ المحركات المفعّلة في هذا البحث",
    options=ALL_ENGINE_NAMES,
    default=ALL_ENGINE_NAMES,
)

# ---------------------------------------------------------
# 3. صيغ البحث المتقدمة (Dorks) الخاصة بيوزر انستغرام
# ---------------------------------------------------------
def generate_instagram_queries(username):
    """توليد كافة صيغ البحث المتقدمة الخاصة بيوزر انستغرام"""
    clean_user = username.strip().replace("@", "").strip()
    if not clean_user:
        return []
    
    queries = [
        f"site:instagram.com/{clean_user}",
        f"site:instagram.com/{clean_user}/",
        f'"instagram.com/{clean_user}"',
        f'intitle:"{clean_user}" site:instagram.com',
        f'"{clean_user}" instagram profile',
        f'site:instagram.com/p/ "{clean_user}"',
        f'site:instagram.com/reel/ "{clean_user}"',
        f'site:instagram.com/stories/ "{clean_user}"',
    ]
    return queries

# ---------------------------------------------------------
# 4. دوال الاستعلام الخاصة بكل محرك
# ---------------------------------------------------------
def fetch_google_results(username, api_key, cx_id, num_results=10):
    results = []
    if not api_key or not cx_id:
        return results
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            params = {"q": q, "key": api_key, "cx": cx_id, "num": min(max(int(num_results), 1), 10)}
            resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                for item in items:
                    results.append({
                        "engine": "Google",
                        "title": item.get("title"),
                        "source": item.get("displayLink"),
                        "snippet": item.get("snippet"),
                        "link": item.get("link")
                    })
        except Exception:
            continue
            
    seen = set()
    unique_results = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique_results.append(r)
    return unique_results

def fetch_bing_results(username, api_key, num_results=10):
    results = []
    if not api_key:
        return results
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            headers = {"Ocp-Apim-Subscription-Key": api_key}
            params = {"q": q, "count": num_results, "textDecorations": False, "textFormat": "RAW"}
            resp = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                pages = resp.json().get("webPages", {}).get("value", [])
                for page in pages:
                    results.append({
                        "engine": "Bing",
                        "title": page.get("name"),
                        "source": page.get("displayUrl"),
                        "snippet": page.get("snippet"),
                        "link": page.get("url")
                    })
        except Exception:
            continue
            
    seen = set()
    unique_results = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique_results.append(r)
    return unique_results

def fetch_brave_results(username, api_key, num_results=10):
    results = []
    if not api_key:
        return results
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
            params = {"q": q, "count": min(max(int(num_results), 1), 20)}
            resp = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params, timeout=10)
            if resp.status_code == 200:
                items = resp.json().get("web", {}).get("results", [])
                for item in items:
                    results.append({
                        "engine": "Brave",
                        "title": item.get("title"),
                        "source": item.get("url"),
                        "snippet": item.get("description"),
                        "link": item.get("url")
                    })
        except Exception:
            continue
            
    seen = set()
    unique_results = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique_results.append(r)
    return unique_results

def _extract_ddg_real_url(href):
    if not href:
        return href
    if href.startswith("//"):
        href = "https:" + href
    if "uddg=" in href:
        parsed = urllib.parse.urlparse(href)
        qs = urllib.parse.parse_qs(parsed.query)
        if qs.get("uddg"):
            return urllib.parse.unquote(qs["uddg"][0])
    return href

def fetch_duckduckgo_results(username, num_results=10):
    results = []
    if not _BS4_AVAILABLE:
        return results
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get("https://html.duckduckgo.com/html/", params={"q": q}, headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select("#links .result") or soup.select(".result")
                for item in items[:num_results]:
                    title_tag = item.select_one(".result__a")
                    if not title_tag:
                        continue
                    title = title_tag.get_text(strip=True)
                    link = _extract_ddg_real_url(title_tag.get("href", ""))
                    snippet_tag = item.select_one(".result__snippet")
                    snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                    source = urllib.parse.urlparse(link).netloc if link else ""
                    results.append({
                        "engine": "DuckDuckGo",
                        "title": title,
                        "source": source,
                        "snippet": snippet,
                        "link": link
                    })
        except Exception:
            continue
            
    seen = set()
    unique_results = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique_results.append(r)
    return unique_results

def fetch_searx_results(username, instance_url, num_results=10):
    results = []
    if not instance_url:
        return results
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            base = instance_url.strip().rstrip("/")
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(f"{base}/search", params={"q": q, "format": "json"}, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:num_results]:
                    link = item.get("url", "")
                    results.append({
                        "engine": "SearxNG",
                        "title": item.get("title"),
                        "source": urllib.parse.urlparse(link).netloc if link else "",
                        "snippet": item.get("content", ""),
                        "link": link
                    })
        except Exception:
            continue
            
    seen = set()
    unique_results = []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique_results.append(r)
    return unique_results

def fetch_wayback_results(username, num_results=15):
    results = []
    clean_user = username.strip().replace("@", "").strip()
    try:
        url = f"https://web.archive.org/cdx/search/cdx?url=instagram.com/{urllib.parse.quote(clean_user)}*&output=json&limit={num_results}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for row in data[1:num_results + 1]:
                    timestamp, original_url = row[1], row[2]
                    archive_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
                    results.append({
                        "engine": "Wayback Archive",
                        "title": f"نسخة مؤرشفة لحساب انستغرام ({timestamp[:8]})",
                        "source": original_url,
                        "snippet": f"رابط مسجل في الأرشيف بتاريخ {timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
                        "link": archive_url
                    })
    except Exception:
        pass
    return results

# ---------------------------------------------------------
# 5. بناء وتشغيل المهام بالتوازي
# ---------------------------------------------------------
def build_tasks(username, cfg, enabled):
    all_tasks = {
        "Google": (fetch_google_results, (username, cfg["google_key"], cfg["cx_id"], cfg["num_results"])),
        "Bing": (fetch_bing_results, (username, cfg["bing_key"], cfg["num_results"])),
        "Brave": (fetch_brave_results, (username, cfg["brave_key"], cfg["num_results"])),
        "DuckDuckGo": (fetch_duckduckgo_results, (username, cfg["num_results"])),
        "SearxNG": (fetch_searx_results, (username, cfg["searx_instance"], cfg["num_results"])),
        "Wayback Archive": (fetch_wayback_results, (username, cfg["num_results"])),
    }
    return {name: t for name, t in all_tasks.items() if name in enabled}

# ---------------------------------------------------------
# 6. دوال التصدير
# ---------------------------------------------------------
def export_to_json(results):
    clean = [{k: v for k, v in r.items() if k != "uid"} for r in results]
    return json.dumps(clean, ensure_ascii=False, indent=2).encode("utf-8")

def export_to_csv(results):
    output = io.StringIO()
    fieldnames = ["engine", "title", "source", "snippet", "link"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in results:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return output.getvalue().encode("utf-8-sig")

# ---------------------------------------------------------
# 7. عرض قائمة النتائج
# ---------------------------------------------------------
def display_results_list(results, tab_key=""):
    if not results:
        st.info("لا توجد نتائج لعرضها لهذا اليوزر. تأكد من تفعيل المحركات وصحة المفاتيح.")
        return
    for idx, item in enumerate(results, 1):
        with st.container(border=True):
            badge = ENGINE_BADGES.get(item.get("engine", ""), "🔹")
            st.markdown(f"**{idx}. {item.get('title') or 'بدون عنوان'}**  {badge} `{item.get('engine', '')}`")
            source = item.get("source") or ""
            link = item.get("link") or ""
            if link:
                st.caption(f"🔗 الرابط: [{source or link}]({link})")
            elif source:
                st.caption(f"🔗 المصدر: {source}")
            st.text_area(
                "المقتطف النصي أو الوصف:",
                value=item.get("snippet") or "",
                height=80,
                key=f"snippet_{tab_key}_{item.get('uid', idx)}",
                label_visibility="collapsed"
            )

# ---------------------------------------------------------
# 8. واجهة البحث الرئيسية
# ---------------------------------------------------------
if "results_map" not in st.session_state:
    st.session_state.results_map = None
    st.session_state.durations = {}
    st.session_state.total_elapsed = 0.0
    st.session_state.last_username = ""

st.subheader("📸 بحث عن حساب انستغرام")
search_username = st.text_input(
    "أدخل يوزر انستغرام المستهدف (بدون @):",
    placeholder='مثال: username'
)

if st.button("🚀 بدء البحث المجمع عن الحساب", type="primary", use_container_width=True):
    if not search_username.strip():
        st.warning("يرجى إدخال يوزر انستغرام صحيح للبحث.")
    elif not enabled_engines:
        st.warning("يرجى تفعيل محرك واحد على الأقل من القائمة الجانبية.")
    else:
        cfg = {
            "google_key": google_api_key,
            "cx_id": google_cx_id,
            "bing_key": bing_api_key,
            "brave_key": brave_api_key,
            "searx_instance": searx_instance,
            "num_results": num_results,
        }
        tasks = build_tasks(search_username, cfg, enabled_engines)
        progress_bar = st.progress(0.0)
        status_area = st.empty()
        start = time.time()
        results_map = {}
        durations = {}
        total = len(tasks)

        with ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
            future_map = {executor.submit(fn, *args): name for name, (fn, args) in tasks.items()}
            done = 0
            for future in as_completed(future_map):
                name = future_map[future]
                try:
                    results_map[name] = future.result()
                except Exception as e:
                    results_map[name] = [{"engine": name, "title": "خطأ", "source": "", "snippet": str(e), "link": ""}]
                done += 1
                elapsed = time.time() - start
                avg = elapsed / done
                eta = avg * (total - done)
                progress_bar.progress(done / total)
                status_area.markdown(
                    f"✅ فحص **{name}** ({done}/{total}) · ⏱️ منقضٍ: {elapsed:.1f}ث"
                )
                durations[name] = elapsed

        progress_bar.empty()
        status_area.empty()
        total_elapsed = time.time() - start

        for items in results_map.values():
            for item in items:
                item["uid"] = str(uuid.uuid4())

        for stale_key in ("sort_choice_widget", "reverse_sort_widget", "engine_filter_widget"):
            st.session_state.pop(stale_key, None)

        st.session_state.results_map = results_map
        st.session_state.durations = durations
        st.session_state.total_elapsed = total_elapsed
        st.session_state.last_username = search_username
        st.success(f"✅ اكتمل البحث خلال {total_elapsed:.1f} ثانية.")

# ---------------------------------------------------------
# 9. عرض النتائج
# ---------------------------------------------------------
if st.session_state.results_map:
    results_map = st.session_state.results_map
    durations = st.session_state.durations
    total_elapsed = st.session_state.total_elapsed
    last_username = st.session_state.last_username

    all_combined = []
    for items in results_map.values():
        all_combined.extend(items)

    st.divider()
    st.subheader(f"📊 نتائج البحث عن اليوزر: \"{last_username}\"")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("إجمالي الروابط", len(all_combined))
    m2.metric("المحركات المستخدمة", len(results_map))
    m3.metric("الوقت الإجمالي", f"{total_elapsed:.1f} ث")
    best_engine = max(results_map, key=lambda k: len(results_map[k])) if results_map else "-"
    m4.metric("أكثر محرك نتائج", best_engine)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "⬇️ تصدير النتائج (JSON)",
            data=export_to_json(all_combined),
            file_name=f"insta_{last_username}_results.json",
            mime="application/json",
            disabled=len(all_combined) == 0,
            use_container_width=True
        )
    with col2:
        st.download_button(
            "⬇️ تصدير النتائج (CSV)",
            data=export_to_csv(all_combined),
            file_name=f"insta_{last_username}_results.csv",
            mime="text/csv",
            disabled=len(all_combined) == 0,
            use_container_width=True
        )
    with col3:
        if st.button("🗑️ مسح النتائج", use_container_width=True):
            st.session_state.results_map = None
            st.rerun()

    sc1, sc2, sc3 = st.columns([2, 1, 2])
    with sc1:
        sort_choice = st.selectbox(
            "ترتيب النتائج حسب:",
            ["الافتراضي", "اسم المحرك", "العنوان (أبجدياً)", "المصدر"],
            key="sort_choice_widget"
        )
    with sc2:
        reverse_sort = st.checkbox("تنازلي", value=False, key="reverse_sort_widget")
    with sc3:
        engine_filter = st.multiselect(
            "تصفية التبويب حسب المحرك:",
            options=list(results_map.keys()),
            default=list(results_map.keys()),
            key="engine_filter_widget"
        )

    def _sort_key(item):
        if sort_choice == "اسم المحرك":
            return item.get("engine", "") or ""
        if sort_choice == "العنوان (أبجدياً)":
            return (item.get("title") or "").lower()
        if sort_choice == "المصدر":
            return (item.get("source") or "").lower()
        return 0

    def _apply_sort(items):
        if sort_choice == "الافتراضي":
            return list(reversed(items)) if reverse_sort else items
        return sorted(items, key=_sort_key, reverse=reverse_sort)

    filtered_all = [it for it in all_combined if it.get("engine") in engine_filter]
    sorted_all = _apply_sort(filtered_all)

    engine_names_in_order = list(results_map.keys())
    tab_labels = [f"الكل ({len(sorted_all)})"] + [
        f"{ENGINE_BADGES.get(name, '')} {name} ({len(results_map[name])})" for name in engine_names_in_order
    ]
    tabs = st.tabs(tab_labels)

    with tabs[0]:
        display_results_list(sorted_all, tab_key="all")

    for i, name in enumerate(engine_names_in_order, start=1):
        with tabs[i]:
            display_results_list(_apply_sort(results_map[name]), tab_key=name)
