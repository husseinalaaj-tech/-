import streamlit as st
import requests
import urllib.parse
import json
import io
import csv
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------
# 1. إعدادات الصفحة والواجهة العامة
# ---------------------------------------------------------
st.set_page_config(
    page_title="Multi-Engine Archive & Search Extractor",
    page_icon="🔎",
    layout="wide"
)

st.markdown("""
<style>
.result-card {
    border: 1px solid rgba(128,128,128,0.25);
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 12px;
    background-color: rgba(128,128,128,0.04);
}
.result-title { font-size: 1.02rem; font-weight: 600; margin-bottom: 2px; }
.result-meta { font-size: 0.8rem; opacity: 0.7; margin-bottom: 6px; }
.engine-badge {
    display: inline-block;
    padding: 1px 9px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    background-color: rgba(99,102,241,0.15);
    color: #6366f1;
    margin-inline-start: 6px;
}
</style>
""", unsafe_allow_html=True)

st.title("🔎 أداة البحث المجمع واستخراج النصوص والأرشيف")
st.markdown(
    "تطبيق مجمّع لاستعلام عدة محركات بحث وأرشيف الإنترنت في نفس اللحظة (تنفيذ متوازٍ)، "
    "مع تصدير النتائج وتنظيمها وترتيبها."
)

# ---------------------------------------------------------
# 2. القائمة الجانبية: مفاتيح الـ API + إعدادات البحث
# ---------------------------------------------------------
st.sidebar.header("⚙️ الإعدادات")

no_key_mode = st.sidebar.toggle(
    "🆓 وضع بلا مفاتيح API (استخدام المحركات المجانية فقط)",
    value=False,
    help="يعمل باستخدام DuckDuckGo وأرشيف Wayback فقط، دون الحاجة لأي مفتاح API."
)

st.sidebar.divider()
st.sidebar.subheader("🔑 مفاتيح المحركات (اختيارية)")

with st.sidebar.expander("Google Custom Search", expanded=not no_key_mode):
    google_api_key = st.text_input("Google API Key", type="password", disabled=no_key_mode, key="g_key")
    google_cx_id = st.text_input("Google CX ID", type="password", disabled=no_key_mode, key="g_cx")

with st.sidebar.expander("Bing Web Search"):
    bing_api_key = st.text_input("Bing Search API Key", type="password", disabled=no_key_mode, key="b_key")

with st.sidebar.expander("Brave Search"):
    brave_api_key = st.text_input("Brave Search API Key", type="password", disabled=no_key_mode, key="br_key")

with st.sidebar.expander("Yandex XML Search"):
    yandex_user = st.text_input("Yandex User", disabled=no_key_mode, key="y_user")
    yandex_key = st.text_input("Yandex API Key", type="password", disabled=no_key_mode, key="y_key")

st.sidebar.divider()
st.sidebar.subheader("🧩 محركات مجانية (لا تحتاج مفتاح)")
use_duckduckgo = st.sidebar.checkbox("DuckDuckGo", value=True)
use_wayback = st.sidebar.checkbox("Wayback Machine (أرشيف الإنترنت)", value=True)

st.sidebar.divider()
results_per_engine = st.sidebar.slider("عدد النتائج من كل محرك", 5, 30, 10)

# ---------------------------------------------------------
# 3. دوال الاستعلام الخاصة بكل محرك
#    كل دالة تُرجع (النتائج, مدة التنفيذ بالثواني)
#    تنسيق موحد لكل نتيجة: engine, title, source, snippet, link
# ---------------------------------------------------------

def fetch_google_results(query, api_key, cx_id, num):
    start = time.time()
    results = []
    if not api_key or not cx_id:
        return results, 0
    try:
        clean_query = query.strip('\'"')
        exact_query = f'"{clean_query}"'
        url = (f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(exact_query)}"
               f"&key={api_key}&cx={cx_id}&num={min(num, 10)}")
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items:
                results.append({
                    "engine": "Google", "title": item.get("title"),
                    "source": item.get("displayLink"), "snippet": item.get("snippet"),
                    "link": item.get("link")
                })
        else:
            results.append({"engine": "Google", "title": f"خطأ HTTP {resp.status_code}",
                             "source": "", "snippet": resp.text[:200], "link": ""})
    except Exception as e:
        results.append({"engine": "Google", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results, round(time.time() - start, 2)


def fetch_bing_results(query, api_key, num):
    start = time.time()
    results = []
    if not api_key:
        return results, 0
    try:
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        clean_query = query.strip('\'"')
        exact_query = f'"{clean_query}"'
        params = {"q": exact_query, "textDecorations": False, "textFormat": "RAW", "count": num}
        url = "https://api.bing.microsoft.com/v7.0/search"
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code == 200:
            pages = resp.json().get("webPages", {}).get("value", [])
            for page in pages:
                results.append({
                    "engine": "Bing", "title": page.get("name"),
                    "source": page.get("displayUrl"), "snippet": page.get("snippet"),
                    "link": page.get("url")
                })
        else:
            results.append({"engine": "Bing", "title": f"خطأ HTTP {resp.status_code}",
                             "source": "", "snippet": resp.text[:200], "link": ""})
    except Exception as e:
        results.append({"engine": "Bing", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results, round(time.time() - start, 2)


def fetch_brave_results(query, api_key, num):
    start = time.time()
    results = []
    if not api_key:
        return results, 0
    try:
        clean_query = query.strip('\'"')
        exact_query = f'"{clean_query}"'
        headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
        params = {"q": exact_query, "count": num}
        url = "https://api.search.brave.com/res/v1/web/search"
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code == 200:
            items = resp.json().get("web", {}).get("results", [])
            for item in items:
                results.append({
                    "engine": "Brave", "title": item.get("title"),
                    "source": item.get("url"), "snippet": item.get("description"),
                    "link": item.get("url")
                })
        else:
            results.append({"engine": "Brave", "title": f"خطأ HTTP {resp.status_code}",
                             "source": "", "snippet": resp.text[:200], "link": ""})
    except Exception as e:
        results.append({"engine": "Brave", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results, round(time.time() - start, 2)


def fetch_yandex_results(query, user, key, num):
    start = time.time()
    results = []
    if not user or not key:
        return results, 0
    try:
        clean_query = query.strip('\'"')
        exact_query = f'"{clean_query}"'
        url = (f"https://yandex.com/search/xml?user={urllib.parse.quote(user)}"
               f"&key={urllib.parse.quote(key)}&query={urllib.parse.quote(exact_query)}"
               f"&l10n=en&sortby=rlv&filter=none&maxpassages=1&groupby=attr%3D%22%22.mode%3Dflat.groups-on-page%3D{num}")
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            # Yandex XML السريع لا يحتاج مكتبة تحليل XML خارجية إضافية غير موجودة، نستخدم regex بسيط بديل عن json
            import re
            docs = re.findall(r"<doc>(.*?)</doc>", resp.text, re.S)
            for doc in docs:
                title_m = re.search(r"<title>(.*?)</title>", doc, re.S)
                url_m = re.search(r"<url>(.*?)</url>", doc, re.S)
                passage_m = re.search(r"<passage>(.*?)</passage>", doc, re.S)
                title = re.sub("<.*?>", "", title_m.group(1)) if title_m else "بدون عنوان"
                link = url_m.group(1) if url_m else ""
                snippet = re.sub("<.*?>", "", passage_m.group(1)) if passage_m else ""
                results.append({
                    "engine": "Yandex", "title": title, "source": link,
                    "snippet": snippet, "link": link
                })
        else:
            results.append({"engine": "Yandex", "title": f"خطأ HTTP {resp.status_code}",
                             "source": "", "snippet": resp.text[:200], "link": ""})
    except Exception as e:
        results.append({"engine": "Yandex", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results, round(time.time() - start, 2)


def fetch_duckduckgo_results(query, num):
    """محرك مجاني لا يحتاج مفتاح API، عبر مكتبة duckduckgo_search إن وُجدت."""
    start = time.time()
    results = []
    try:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            results.append({"engine": "DuckDuckGo", "title": "مكتبة غير مثبتة",
                             "source": "", "snippet": "يرجى تثبيت الحزمة: pip install duckduckgo-search", "link": ""})
            return results, round(time.time() - start, 2)
        clean_query = query.strip('\'"')
        exact_query = f'"{clean_query}"'
        with DDGS() as ddgs:
            for item in ddgs.text(exact_query, max_results=num):
                results.append({
                    "engine": "DuckDuckGo", "title": item.get("title"),
                    "source": item.get("href"), "snippet": item.get("body"),
                    "link": item.get("href")
                })
    except Exception as e:
        results.append({"engine": "DuckDuckGo", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results, round(time.time() - start, 2)


def fetch_wayback_results(query, num):
    """استعلام أرشيف الإنترنت Wayback Machine (لا يتطلب مفتاح API)"""
    start = time.time()
    results = []
    try:
        url = f"https://web.archive.org/cdx/search/cdx?url=*{urllib.parse.quote(query)}*&output=json&limit={num}"
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for row in data[1:]:
                    timestamp, original_url = row[1], row[2]
                    archive_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
                    results.append({
                        "engine": "Wayback Archive",
                        "title": f"نسخة مؤرشفة ({timestamp[:8]})",
                        "source": original_url,
                        "snippet": f"الصفحة مؤرشفة بتاريخ {timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
                        "link": archive_url
                    })
    except Exception as e:
        results.append({"engine": "Wayback Archive", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results, round(time.time() - start, 2)


# ---------------------------------------------------------
# 4. تنفيذ الاستعلامات بالتوازي
# ---------------------------------------------------------

def run_all_engines(query, cfg, num, status_placeholder, progress_bar):
    tasks = {}
    if not no_key_mode:
        if cfg["google_key"] and cfg["google_cx"]:
            tasks["Google"] = (fetch_google_results, (query, cfg["google_key"], cfg["google_cx"], num))
        if cfg["bing_key"]:
            tasks["Bing"] = (fetch_bing_results, (query, cfg["bing_key"], num))
        if cfg["brave_key"]:
            tasks["Brave"] = (fetch_brave_results, (query, cfg["brave_key"], num))
        if cfg["yandex_user"] and cfg["yandex_key"]:
            tasks["Yandex"] = (fetch_yandex_results, (query, cfg["yandex_user"], cfg["yandex_key"], num))
    if cfg["use_duckduckgo"]:
        tasks["DuckDuckGo"] = (fetch_duckduckgo_results, (query, num))
    if cfg["use_wayback"]:
        tasks["Wayback"] = (fetch_wayback_results, (query, num))

    if not tasks:
        return {}, {}

    results_map = {name: [] for name in tasks}
    timings = {name: 0 for name in tasks}
    completed = 0
    total = len(tasks)
    overall_start = time.time()

    with ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
        future_to_name = {executor.submit(func, *args): name for name, (func, args) in tasks.items()}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                res, duration = future.result()
                results_map[name] = res
                timings[name] = duration
            except Exception as e:
                results_map[name] = [{"engine": name, "title": "خطأ غير متوقع", "source": "", "snippet": str(e), "link": ""}]
                timings[name] = round(time.time() - overall_start, 2)
            completed += 1
            elapsed = round(time.time() - overall_start, 2)
            status_placeholder.markdown(
                f"✅ اكتمل **{name}** ({len(results_map[name])} نتيجة) — الوقت المنقضي: {elapsed} ث "
                f"({completed}/{total} محركات)"
            )
            progress_bar.progress(completed / total)

    return results_map, timings


# ---------------------------------------------------------
# 5. دوال التصدير (JSON / CSV)
# ---------------------------------------------------------

def export_to_json(results):
    return json.dumps(results, ensure_ascii=False, indent=2).encode("utf-8")


def export_to_csv(results):
    output = io.StringIO()
    fieldnames = ["engine", "title", "source", "snippet", "link"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in results:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return output.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------
# 6. واجهة البحث الرئيسية
# ---------------------------------------------------------

search_col, sort_col = st.columns([3, 1])
with search_col:
    search_query = st.text_input(
        "أدخل النص أو العبارة الحرفية المراد البحث عنها:",
        placeholder='مثال: "نص التعليق المطلوب"'
    )
with sort_col:
    sort_option = st.selectbox(
        "ترتيب النتائج حسب:",
        ["الافتراضي", "المحرك", "العنوان (أبجدي)", "المصدر (أبجدي)"]
    )

run_clicked = st.button("🚀 تشغيل البحث المجمع", type="primary", use_container_width=True)

if run_clicked:
    if not search_query.strip():
        st.warning("يرجى إدخال نص للبحث.")
    else:
        cfg = {
            "google_key": google_api_key, "google_cx": google_cx_id,
            "bing_key": bing_api_key, "brave_key": brave_api_key,
            "yandex_user": yandex_user, "yandex_key": yandex_key,
            "use_duckduckgo": use_duckduckgo, "use_wayback": use_wayback,
        }

        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        overall_start = time.time()

        results_map, timings = run_all_engines(search_query, cfg, results_per_engine, status_placeholder, progress_bar)

        total_elapsed = round(time.time() - overall_start, 2)
        progress_bar.empty()

        if not results_map:
            status_placeholder.empty()
            st.error("لم يتم تفعيل أي محرك بحث. فعّل «وضع بلا مفاتيح» أو أدخل مفتاح API واحد على الأقل.")
        else:
            status_placeholder.success(f"انتهى البحث في {total_elapsed} ثانية عبر {len(results_map)} محرك/مصدر.")

            all_combined = []
            for name, res in results_map.items():
                all_combined.extend(res)

            # ترتيب النتائج
            if sort_option == "المحرك":
                all_combined.sort(key=lambda r: r.get("engine", ""))
            elif sort_option == "العنوان (أبجدي)":
                all_combined.sort(key=lambda r: (r.get("title") or "").lower())
            elif sort_option == "المصدر (أبجدي)":
                all_combined.sort(key=lambda r: (r.get("source") or "").lower())

            # ملخص سريع لعدد النتائج ووقت كل محرك
            summary_cols = st.columns(len(results_map) if results_map else 1)
            for i, (name, res) in enumerate(results_map.items()):
                with summary_cols[i]:
                    st.metric(label=name, value=len(res), delta=f"{timings.get(name, 0)} ث")

            st.divider()

            # أزرار التصدير
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "⬇️ تصدير كل النتائج (JSON)",
                    data=export_to_json(all_combined),
                    file_name="search_results.json",
                    mime="application/json",
                    disabled=len(all_combined) == 0,
                    use_container_width=True
                )
            with col2:
                st.download_button(
                    "⬇️ تصدير كل النتائج (CSV)",
                    data=export_to_csv(all_combined),
                    file_name="search_results.csv",
                    mime="text/csv",
                    disabled=len(all_combined) == 0,
                    use_container_width=True
                )

            # تبويبات النتائج
            tab_labels = [f"الكل ({len(all_combined)})"] + [f"{name} ({len(res)})" for name, res in results_map.items()]
            tabs = st.tabs(tab_labels)

            def display_results_list(results):
                if not results:
                    st.info("لا توجد نتائج متوفرة لهذا المصدر حاليًا (تحقق من مفتاح الـ API أو صياغة البحث).")
                    return
                for item in results:
                    unique_id = uuid.uuid4().hex[:8]
                    with st.container():
                        st.markdown(
                            f"<div class='result-card'>"
                            f"<div class='result-title'>{item.get('title') or 'بدون عنوان'}"
                            f"<span class='engine-badge'>{item.get('engine','')}</span></div>"
                            f"<div class='result-meta'>المصدر: {item.get('source','')}</div>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                        if item.get("link"):
                            st.caption(f"🔗 [{item['link']}]({item['link']})")
                        st.text_area(
                            "المقتطف النصي:",
                            value=item.get("snippet") or "",
                            height=80,
                            key=f"snippet_{unique_id}",
                            label_visibility="collapsed"
                        )
                        st.divider()

            with tabs[0]:
                display_results_list(all_combined)
            for i, (name, res) in enumerate(results_map.items(), start=1):
                with tabs[i]:
                    display_results_list(res)

st.divider()
with st.expander("ℹ️ ملاحظات الاستخدام"):
    st.markdown("""
- **وضع بلا مفاتيح**: يفعّل DuckDuckGo وأرشيف Wayback فقط دون أي مفتاح API.
- **Google / Bing / Brave / Yandex**: تحتاج مفاتيح API صالحة تُدخل من الشريط الجانبي.
- يتم تشغيل جميع المحركات المفعّلة بالتوازي لتقليل وقت الانتظار الكلي.
- روابط أرشيف Wayback تُبنى دائمًا بصيغة `https://` لتفادي رفض الطلبات غير المشفّرة.
- كل نتيجة تحصل على مُعرّف فريد (UUID) لعنصر الواجهة، لتفادي أي تعارض في المفاتيح حتى لو تكرر الرابط أو كان فارغًا.
""")
