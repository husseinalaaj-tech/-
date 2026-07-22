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
    page_title="Multi-Engine Archive & Search Extractor",
    page_icon="🔎",
    layout="wide"
)

# تحسينات بصرية بسيطة لدعم النص العربي (محاذاة يمين) دون كسر تخطيط Streamlit الداخلي
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

st.title("🔎 أداة البحث المجمع واستخراج النصوص والأرشيف")
st.markdown(
    "تطبيق مجمع لاستعلام محركات البحث والأرشيفات وجلب المقتطفات النصية مباشرة "
    "(تنفيذ متوازٍ + تقدّم حي + ترتيب وتصفية + تصدير النتائج)."
)

with st.expander("ℹ️ طريقة الاستخدام (اضغط للفتح)", expanded=False):
    st.markdown("""
1. **من القائمة الجانبية**: فعّل المحركات المجانية (مفعّلة تلقائياً) و/أو أدخل مفاتيح API للمحركات التي تملك مفاتيح لها.
2. **في الأسفل**: اكتب النص أو العبارة المراد البحث عنها، ثم اضغط زر **تشغيل البحث المجمع**.
3. أثناء التنفيذ ستظهر نسبة الإنجاز والوقت المتبقي التقديري لكل محرك.
4. بعد الانتهاء تظهر ملخصات سريعة، ثم يمكنك **ترتيب** و**تصفية** النتائج، وتصديرها كـ JSON أو CSV.
5. النتائج تبقى معروضة حتى لو غيّرت خيار الترتيب — لن تختفي إلا بالضغط على "مسح النتائج" أو بحث جديد.
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

st.sidebar.header("⚙️ الإعدادات العامة")
num_results = st.sidebar.slider("عدد النتائج المطلوبة من كل محرك", min_value=3, max_value=20, value=10, step=1)
exact_match = st.sidebar.checkbox(
    "بحث عن نص حرفي بالضبط (Exact Phrase)", value=True,
    help="عند التفعيل، يوضع النص بين علامتي اقتباس في الاستعلام لطلب تطابق حرفي من المحركات التي تدعم ذلك."
)

st.sidebar.divider()
st.sidebar.header("🆓 محركات لا تحتاج مفتاح API")

with st.sidebar.expander("🦆 DuckDuckGo", expanded=False):
    st.caption("بحث نصي فعلي داخل الصفحات، عبر النسخة الثابتة من الموقع (بدون تسجيل أو مفتاح).")
    if not _BS4_AVAILABLE:
        st.warning("مكتبة beautifulsoup4 غير مثبتة. نفّذ: pip install beautifulsoup4")

with st.sidebar.expander("🔎 SearxNG (محرك بحث تجميعي مجاني)", expanded=False):
    searx_instance = st.text_input(
        "رابط خادم SearxNG (Instance URL)",
        value="https://searx.be",
        help="بعض الخوادم العامة تُعطّل صيغة JSON. إن لم تظهر نتائج، جرّب رابط خادم SearxNG عام آخر."
    )
    st.caption("SearxNG يجمع نتائج من عدة محركات في آن واحد، ولا يتطلب مفتاح API.")

with st.sidebar.expander("🗄️ Wayback Machine (أرشيف الإنترنت)", expanded=False):
    st.caption(
        "⚠️ ملاحظة مهمة: هذا الأرشيف يبحث في **الروابط (URLs)** المؤرشفة فقط، وليس في نص الصفحة. "
        "لذا فهو أنسب للبحث عن نطاق أو رابط محدد، وليس عبارة نصية عامة."
    )

st.sidebar.divider()
st.sidebar.header("🔑 محركات تتطلب مفتاح API")

with st.sidebar.expander("🟦 Google Custom Search", expanded=False):
    google_api_key = st.text_input("Google API Key", type="password", key="google_api_key")
    google_cx_id = st.text_input("Google Custom Search (CX ID)", type="password", key="google_cx_id")
    st.caption("احصل على المفتاح ومعرف CX من developers.google.com/custom-search")

with st.sidebar.expander("🦁 Brave Search API", expanded=False):
    brave_api_key = st.text_input("Brave Search API Key", type="password", key="brave_api_key")
    st.caption("ملاحظة: أنهت Brave خطتها المجانية مطلع 2026، وأصبحت تعتمد على رصيد مدفوع مسبقاً بدلاً من طبقة مجانية دائمة.")

with st.sidebar.expander("🟪 Bing Search API (متوقفة نهائياً ⚠️)", expanded=False):
    bing_api_key = st.text_input("Bing Search API Key", type="password", key="bing_api_key")
    st.warning(
        "أوقفت مايكروسوفت خدمة Bing Search API نهائياً في 11 أغسطس 2025، ولم تعد المفاتيح — "
        "حتى القديمة منها — تعمل. تم إبقاء الحقل لأغراض التوافق فقط، ومن المتوقع ألا يُعيد أي نتائج."
    )

st.sidebar.divider()
enabled_engines = st.sidebar.multiselect(
    "✅ المحركات المفعّلة في هذا البحث",
    options=ALL_ENGINE_NAMES,
    default=ALL_ENGINE_NAMES,
    help="يمكنك استبعاد أي محرك حتى لو أدخلت مفتاحه، لتوفير الوقت أو تجنّب استهلاك الحصة."
)

# ---------------------------------------------------------
# 3. دوال الاستعلام الخاصة بكل محرك
#    كل دالة تُرجع قائمة قواميس بتنسيق موحد:
#    engine, title, source, snippet, link
# ---------------------------------------------------------

def _clean(query):
    return query.strip().strip('\'"')

def fetch_google_results(query, api_key, cx_id, exact=True, num_results=10):
    """استعلام محرك Google Custom Search"""
    results = []
    if not api_key or not cx_id:
        return results
    try:
        clean_query = _clean(query)
        q = f'"{clean_query}"' if exact else clean_query
        params = {"q": q, "key": api_key, "cx": cx_id, "num": min(max(int(num_results), 1), 10)}
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items[:num_results]:
                results.append({
                    "engine": "Google",
                    "title": item.get("title"),
                    "source": item.get("displayLink"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link")
                })
        else:
            results.append({"engine": "Google", "title": f"خطأ HTTP {resp.status_code}", "source": "", "snippet": resp.text[:200], "link": ""})
    except Exception as e:
        results.append({"engine": "Google", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results

def fetch_bing_results(query, api_key, exact=True, num_results=10):
    """
    استعلام Bing Web Search API v7.
    ⚠️ ملاحظة: أوقفت مايكروسوفت هذه الخدمة نهائياً في 11 أغسطس 2025.
    تم إبقاء الدالة لأغراض التوافق فقط، ومن المتوقع أن تفشل حتى مع مفتاح صالح سابقاً.
    """
    results = []
    if not api_key:
        return results
    try:
        clean_query = _clean(query)
        q = f'"{clean_query}"' if exact else clean_query
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {"q": q, "count": num_results, "textDecorations": False, "textFormat": "RAW"}
        resp = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            pages = resp.json().get("webPages", {}).get("value", [])
            for page in pages[:num_results]:
                results.append({
                    "engine": "Bing",
                    "title": page.get("name"),
                    "source": page.get("displayUrl"),
                    "snippet": page.get("snippet"),
                    "link": page.get("url")
                })
        else:
            results.append({
                "engine": "Bing",
                "title": f"خطأ HTTP {resp.status_code}",
                "source": "",
                "snippet": "من المرجح أن السبب هو توقف Bing Search API نهائياً منذ أغسطس 2025.",
                "link": ""
            })
    except Exception as e:
        results.append({"engine": "Bing", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results

def fetch_brave_results(query, api_key, exact=True, num_results=10):
    """استعلام Brave Search API"""
    results = []
    if not api_key:
        return results
    try:
        clean_query = _clean(query)
        q = f'"{clean_query}"' if exact else clean_query
        headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
        params = {"q": q, "count": min(max(int(num_results), 1), 20)}
        resp = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("web", {}).get("results", [])
            for item in items[:num_results]:
                results.append({
                    "engine": "Brave",
                    "title": item.get("title"),
                    "source": item.get("url"),
                    "snippet": item.get("description"),
                    "link": item.get("url")
                })
        else:
            results.append({"engine": "Brave", "title": f"خطأ HTTP {resp.status_code}", "source": "", "snippet": resp.text[:200], "link": ""})
    except Exception as e:
        results.append({"engine": "Brave", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results

def _extract_ddg_real_url(href):
    """يفكّ رابط إعادة التوجيه الذي تستخدمه نسخة DuckDuckGo الثابتة إن وُجد"""
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

def fetch_duckduckgo_results(query, exact=True, num_results=10):
    """استعلام DuckDuckGo عبر النسخة الثابتة (HTML) — لا يتطلب مفتاح API"""
    results = []
    if not _BS4_AVAILABLE:
        results.append({
            "engine": "DuckDuckGo", "title": "مكتبة مفقودة", "source": "",
            "snippet": "يرجى تثبيت المكتبة عبر: pip install beautifulsoup4", "link": ""
        })
        return results
    try:
        clean_query = _clean(query)
        q = f'"{clean_query}"' if exact else clean_query
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
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
        else:
            results.append({"engine": "DuckDuckGo", "title": f"خطأ HTTP {resp.status_code}", "source": "", "snippet": "", "link": ""})
    except Exception as e:
        results.append({"engine": "DuckDuckGo", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results

def fetch_searx_results(query, instance_url, exact=True, num_results=10):
    """استعلام خادم SearxNG عام عبر واجهة JSON — لا يتطلب مفتاح API"""
    results = []
    if not instance_url:
        return results
    try:
        clean_query = _clean(query)
        q = f'"{clean_query}"' if exact else clean_query
        base = instance_url.strip().rstrip("/")
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(f"{base}/search", params={"q": q, "format": "json"}, headers=headers, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                results.append({
                    "engine": "SearxNG", "title": "الخادم لا يدعم صيغة JSON", "source": instance_url,
                    "snippet": "جرّب رابط خادم SearxNG عام آخر يدعم format=json.", "link": ""
                })
                return results
            for item in data.get("results", [])[:num_results]:
                link = item.get("url", "")
                results.append({
                    "engine": "SearxNG",
                    "title": item.get("title"),
                    "source": urllib.parse.urlparse(link).netloc if link else "",
                    "snippet": item.get("content", ""),
                    "link": link
                })
        else:
            results.append({
                "engine": "SearxNG", "title": f"خطأ HTTP {resp.status_code}", "source": instance_url,
                "snippet": "قد يكون هذا الخادم يحظر صيغة JSON أو غير متاح حالياً.", "link": ""
            })
    except Exception as e:
        results.append({"engine": "SearxNG", "title": "خطأ في الاتصال", "source": "", "snippet": str(e), "link": ""})
    return results

def fetch_wayback_results(query, num_results=10):
    """استعلام أرشيف الإنترنت Wayback Machine (لا يتطلب مفتاح API، يطابق الروابط فقط)"""
    results = []
    try:
        clean_query = _clean(query)
        url = f"https://web.archive.org/cdx/search/cdx?url=*{urllib.parse.quote(clean_query)}*&output=json&limit={num_results}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for row in data[1:num_results + 1]:
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
    return results

# ---------------------------------------------------------
# 4. بناء وتشغيل المهام بالتوازي (Async/Parallel Execution)
# ---------------------------------------------------------

def build_tasks(query, cfg, enabled):
    all_tasks = {
        "Google": (fetch_google_results, (query, cfg["google_key"], cfg["cx_id"], cfg["exact"], cfg["num_results"])),
        "Bing": (fetch_bing_results, (query, cfg["bing_key"], cfg["exact"], cfg["num_results"])),
        "Brave": (fetch_brave_results, (query, cfg["brave_key"], cfg["exact"], cfg["num_results"])),
        "DuckDuckGo": (fetch_duckduckgo_results, (query, cfg["exact"], cfg["num_results"])),
        "SearxNG": (fetch_searx_results, (query, cfg["searx_instance"], cfg["exact"], cfg["num_results"])),
        "Wayback Archive": (fetch_wayback_results, (query, cfg["num_results"])),
    }
    return {name: t for name, t in all_tasks.items() if name in enabled}

# ---------------------------------------------------------
# 5. دوال التصدير (Export to JSON / CSV)
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
    # utf-8-sig يضمن ظهور النص العربي بشكل صحيح عند فتح الملف في Excel
    return output.getvalue().encode("utf-8-sig")

# ---------------------------------------------------------
# 6. عرض قائمة النتائج (مفاتيح واجهة فريدة عبر uid)
# ---------------------------------------------------------

def display_results_list(results):
    if not results:
        st.info("لا توجد نتائج لعرضها. تحقق من تفعيل المحرك أو صحة مفتاح الـ API.")
        return
    for idx, item in enumerate(results, 1):
        with st.container(border=True):
            badge = ENGINE_BADGES.get(item.get("engine", ""), "🔹")
            st.markdown(f"**{idx}. {item.get('title') or 'بدون عنوان'}**  {badge} `{item.get('engine', '')}`")
            source = item.get("source") or ""
            link = item.get("link") or ""
            if link:
                st.caption(f"🔗 المصدر: [{source or link}]({link})")
            elif source:
                st.caption(f"🔗 المصدر: {source}")
            st.text_area(
                "المقتطف النصي المستخرج:",
                value=item.get("snippet") or "",
                height=80,
                key=f"snippet_{item.get('uid', idx)}",
                label_visibility="collapsed"
            )

# ---------------------------------------------------------
# 7. واجهة البحث الرئيسية
# ---------------------------------------------------------
if "results_map" not in st.session_state:
    st.session_state.results_map = None
    st.session_state.durations = {}
    st.session_state.total_elapsed = 0.0
    st.session_state.last_query = ""

st.subheader("🔍 ابدأ البحث")
search_query = st.text_input(
    "أدخل النص أو الكلمة الحرفية المراد البحث عنها عبر المحركات:",
    placeholder='مثال: نص التعليق المطلوب'
)

if st.button("🚀 تشغيل البحث المجمع", type="primary", use_container_width=True):
    if not search_query.strip():
        st.warning("يرجى إدخال نص للبحث.")
    elif not enabled_engines:
        st.warning("يرجى تفعيل محرك واحد على الأقل من القائمة الجانبية.")
    else:
        cfg = {
            "google_key": google_api_key,
            "cx_id": google_cx_id,
            "bing_key": bing_api_key,
            "brave_key": brave_api_key,
            "searx_instance": searx_instance,
            "exact": exact_match,
            "num_results": num_results,
        }
        tasks = build_tasks(search_query, cfg, enabled_engines)
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
                    results_map[name] = [{"engine": name, "title": "خطأ غير متوقع", "source": "", "snippet": str(e), "link": ""}]
                done += 1
                elapsed = time.time() - start
                avg = elapsed / done
                eta = avg * (total - done)
                progress_bar.progress(done / total)
                status_area.markdown(
                    f"✅ اكتمل **{name}** ({done}/{total}) · ⏱️ منقضٍ: {elapsed:.1f}ث · متبقٍ تقريباً: {eta:.1f}ث"
                )
                durations[name] = elapsed

        progress_bar.empty()
        status_area.empty()
        total_elapsed = time.time() - start

        # تعيين معرّف فريد لكل نتيجة لضمان عدم تعارض مفاتيح عناصر واجهة Streamlit
        for items in results_map.values():
            for item in items:
                item["uid"] = str(uuid.uuid4())

        st.session_state.results_map = results_map
        st.session_state.durations = durations
        st.session_state.total_elapsed = total_elapsed
        st.session_state.last_query = search_query
        st.success(f"✅ اكتمل البحث خلال {total_elapsed:.1f} ثانية عبر {total} محرك.")

# ---------------------------------------------------------
# 8. عرض النتائج (يبقى ظاهراً عبر session_state حتى عند تغيير الترتيب/التصفية)
# ---------------------------------------------------------
if st.session_state.results_map:
    results_map = st.session_state.results_map
    durations = st.session_state.durations
    total_elapsed = st.session_state.total_elapsed
    last_query = st.session_state.last_query

    all_combined = []
    for items in results_map.values():
        all_combined.extend(items)

    st.divider()
    st.subheader(f"📊 نتائج البحث عن: \"{last_query}\"")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("إجمالي النتائج", len(all_combined))
    m2.metric("عدد المحركات المستخدَمة", len(results_map))
    m3.metric("الوقت الإجمالي", f"{total_elapsed:.1f} ث")
    best_engine = max(results_map, key=lambda k: len(results_map[k])) if results_map else "-"
    m4.metric("أكثر محرك نتائج", best_engine)

    col1, col2, col3 = st.columns(3)
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
    with col3:
        if st.button("🗑️ مسح النتائج", use_container_width=True):
            st.session_state.results_map = None
            st.rerun()

    sc1, sc2, sc3 = st.columns([2, 1, 2])
    with sc1:
        sort_choice = st.selectbox(
            "ترتيب النتائج حسب:",
            ["الافتراضي", "اسم المحرك", "العنوان (أبجدياً)", "المصدر"]
        )
    with sc2:
        reverse_sort = st.checkbox("تنازلي", value=False)
    with sc3:
        engine_filter = st.multiselect(
            "تصفية تبويب 'الكل' حسب المحرك:",
            options=list(results_map.keys()),
            default=list(results_map.keys())
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
        display_results_list(sorted_all)

    for i, name in enumerate(engine_names_in_order, start=1):
        with tabs[i]:
            dur = durations.get(name)
            if dur is not None:
                st.caption(f"⏱️ استغرق هذا المحرك حوالي {dur:.1f} ثانية")
            if name == "Wayback Archive":
                st.caption("ℹ️ هذا الأرشيف يطابق الروابط (URLs) وليس نص الصفحة — مناسب أكثر للبحث عن نطاق أو رابط محدد.")
            display_results_list(_apply_sort(results_map[name]))
