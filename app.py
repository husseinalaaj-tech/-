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
# 1. إعدادات الصفحة
# ---------------------------------------------------------
st.set_page_config(
    page_title="Instagram OSINT Search",
    page_icon="📸",
    layout="wide"
)

st.markdown("""
<style>
    div[data-testid="stMarkdownContainer"] p, li, h1, h2, h3, h4 { direction: rtl; text-align: right; }
    .stTextInput input, .stTextArea textarea { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

st.title("📸 أداة البحث المجمع عن حسابات انستغرام (OSINT)")
st.info("ملاحظة: المحركات المجانية قد تحظر طلباتك إذا قمت بالبحث بشكل متكرر وسريع. إذا لم تظهر نتائج من محرك معين، تحقق من سجل الأخطاء في الأسفل.")

# ---------------------------------------------------------
# 2. الإعدادات الجانبية
# ---------------------------------------------------------
ENGINE_BADGES = {
    "Yahoo Search": "🟣",
    "DuckDuckGo": "🦆",
    "SearxNG": "🔎",
    "Wayback Archive": "🗄️",
    "Google": "🟦",
    "Brave": "🦁",
}
ALL_ENGINE_NAMES = list(ENGINE_BADGES.keys())

st.sidebar.header("⚙️ إعدادات البحث")
num_results = st.sidebar.slider("عدد النتائج لكل صيغة", 3, 20, 10)

st.sidebar.divider()
st.sidebar.header("🆓 محركات مجانية (لا تحتاج API)")
st.sidebar.caption("تمت إضافة Yahoo لكونه الأكثر استقراراً في السحب المجاني.")

searx_instance = st.sidebar.text_input("رابط SearxNG", value="https://searx.be")

st.sidebar.divider()
st.sidebar.header("🔑 محركات تحتاج API (للنتائج المضمونة)")
google_api_key = st.sidebar.text_input("Google API Key", type="password")
google_cx_id = st.sidebar.text_input("Google CX ID", type="password")
brave_api_key = st.sidebar.text_input("Brave API Key", type="password")

enabled_engines = st.sidebar.multiselect(
    "✅ المحركات المفعّلة",
    options=ALL_ENGINE_NAMES,
    default=["Yahoo Search", "DuckDuckGo", "Wayback Archive"]
)

# Headers قياسية لتجاوز الحظر
STD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# ---------------------------------------------------------
# 3. توليد الصيغ (Dorks)
# ---------------------------------------------------------
def generate_instagram_queries(username):
    clean_user = username.strip().replace("@", "")
    if not clean_user: return []
    return [
        f"site:instagram.com/{clean_user}",
        f'"{clean_user}" site:instagram.com',
        f'intitle:"{clean_user}" site:instagram.com',
    ]

# ---------------------------------------------------------
# 4. محركات البحث
# ---------------------------------------------------------

def fetch_yahoo_results(username, num_results=10):
    results = []
    errors = []
    if not _BS4_AVAILABLE: return results, ["BeautifulSoup غير مثبت."]
    
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            url = f"https://search.yahoo.com/search?p={urllib.parse.quote(q)}&n={num_results}"
            resp = requests.get(url, headers=STD_HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for div in soup.find_all("div", class_="compTitle"):
                    a_tag = div.find("a")
                    if a_tag and "href" in a_tag.attrs:
                        results.append({
                            "engine": "Yahoo Search",
                            "title": a_tag.text,
                            "source": "instagram.com",
                            "snippet": "نتيجة مستخرجة من ياهو",
                            "link": a_tag["href"]
                        })
            else:
                errors.append(f"Yahoo رد بكود {resp.status_code}")
        except Exception as e:
            errors.append(f"خطأ Yahoo: {str(e)}")
            time.sleep(1)
            
    return _deduplicate(results), errors

def fetch_duckduckgo_lite(username, num_results=10):
    results, errors = [], []
    if not _BS4_AVAILABLE: return results, ["BeautifulSoup غير مثبت."]
    
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            url = "https://lite.duckduckgo.com/lite/"
            data = {"q": q, "kl": "wt-wt"}
            resp = requests.post(url, headers=STD_HEADERS, data=data, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for a_tag in soup.find_all("a", class_="result-url"):
                    link = a_tag.get("href", "")
                    if "instagram.com" in link:
                        results.append({
                            "engine": "DuckDuckGo",
                            "title": a_tag.text,
                            "source": "instagram.com",
                            "snippet": "نتيجة مستخرجة من DDG",
                            "link": link
                        })
            else:
                errors.append(f"DDG حظر الطلب بكود {resp.status_code}")
        except Exception as e:
            errors.append(f"خطأ DDG: {str(e)}")
            time.sleep(1)
            
    return _deduplicate(results), errors

def fetch_searx_results(username, instance_url, num_results=10):
    results, errors = [], []
    if not instance_url: return results, ["رابط الخادم مفقود"]
    
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            base = instance_url.strip().rstrip("/")
            resp = requests.get(f"{base}/search", params={"q": q, "format": "json"}, headers=STD_HEADERS, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", [])[:num_results]:
                    results.append({
                        "engine": "SearxNG",
                        "title": item.get("title", ""),
                        "source": "instagram.com",
                        "snippet": item.get("content", ""),
                        "link": item.get("url", "")
                    })
            else:
                errors.append(f"SearxNG حظر الطلب (ربما لا يدعم JSON) - كود {resp.status_code}")
        except Exception as e:
            errors.append(f"خطأ SearxNG: {str(e)}")
            
    return _deduplicate(results), errors

def fetch_wayback_results(username, num_results=10):
    results, errors = [], []
    clean_user = username.strip().replace("@", "")
    try:
        url = f"https://web.archive.org/cdx/search/cdx?url=instagram.com/{urllib.parse.quote(clean_user)}*&output=json&limit={num_results}"
        resp = requests.get(url, headers=STD_HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for row in data[1:]:
                    ts, orig = row[1], row[2]
                    results.append({
                        "engine": "Wayback Archive",
                        "title": f"أرشيف انستغرام ({ts[:8]})",
                        "source": orig,
                        "snippet": f"مؤرشف بتاريخ {ts[:4]}-{ts[4:6]}-{ts[6:8]}",
                        "link": f"https://web.archive.org/web/{ts}/{orig}"
                    })
        else:
            errors.append(f"Wayback رد بكود {resp.status_code}")
    except Exception as e:
        errors.append(f"خطأ أرشيف: {str(e)}")
        
    return _deduplicate(results), errors

def fetch_google_results(username, api_key, cx_id, num_results=10):
    results, errors = [], []
    if not api_key or not cx_id: return results, ["مفاتيح Google API مفقودة."]
    
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            params = {"q": q, "key": api_key, "cx": cx_id, "num": min(int(num_results), 10)}
            resp = requests.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=15)
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    results.append({
                        "engine": "Google",
                        "title": item.get("title"),
                        "source": item.get("displayLink"),
                        "snippet": item.get("snippet"),
                        "link": item.get("link")
                    })
            else:
                errors.append(f"Google API خطأ: {resp.json().get('error', {}).get('message', resp.status_code)}")
        except Exception as e:
            errors.append(f"خطأ Google: {str(e)}")
            
    return _deduplicate(results), errors

def fetch_brave_results(username, api_key, num_results=10):
    results, errors = [], []
    if not api_key: return results, ["مفتاح Brave API مفقود."]
    
    queries = generate_instagram_queries(username)
    for q in queries:
        try:
            headers = {"X-Subscription-Token": api_key, "Accept": "application/json"}
            resp = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params={"q": q}, timeout=15)
            if resp.status_code == 200:
                for item in resp.json().get("web", {}).get("results", []):
                    results.append({
                        "engine": "Brave",
                        "title": item.get("title"),
                        "source": "instagram.com",
                        "snippet": item.get("description"),
                        "link": item.get("url")
                    })
            else:
                errors.append(f"Brave رد بكود {resp.status_code}")
        except Exception as e:
            errors.append(f"خطأ Brave: {str(e)}")
            
    return _deduplicate(results), errors

def _deduplicate(results):
    seen, unique = set(), []
    for r in results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique.append(r)
    return unique

# ---------------------------------------------------------
# 5. إدارة المهام المتوازية
# ---------------------------------------------------------
def run_all_tasks(username, cfg, enabled):
    tasks_map = {
        "Yahoo Search": lambda: fetch_yahoo_results(username, cfg["num_results"]),
        "DuckDuckGo": lambda: fetch_duckduckgo_lite(username, cfg["num_results"]),
        "SearxNG": lambda: fetch_searx_results(username, cfg["searx"], cfg["num_results"]),
        "Wayback Archive": lambda: fetch_wayback_results(username, cfg["num_results"]),
        "Google": lambda: fetch_google_results(username, cfg["g_key"], cfg["g_cx"], cfg["num_results"]),
        "Brave": lambda: fetch_brave_results(username, cfg["b_key"], cfg["num_results"]),
    }
    
    results_map, errors_map = {}, {}
    active_tasks = {name: func for name, func in tasks_map.items() if name in enabled}
    
    with ThreadPoolExecutor(max_workers=len(active_tasks) or 1) as executor:
        future_to_name = {executor.submit(func): name for name, func in active_tasks.items()}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                res, errs = future.result()
                results_map[name] = res
                if errs: errors_map[name] = list(set(errs))
            except Exception as e:
                results_map[name] = []
                errors_map[name] = [f"انهيار كامل للمحرك: {str(e)}"]
                
    return results_map, errors_map

# ---------------------------------------------------------
# 6. الواجهة الرئيسية للبحث وعرض النتائج
# ---------------------------------------------------------
search_username = st.text_input("أدخل يوزر انستغرام (بدون @):", placeholder="مثال: username")

if st.button("🚀 بدء البحث", type="primary", use_container_width=True):
    if not search_username.strip():
        st.warning("أدخل يوزر للبحث.")
    elif not enabled_engines:
        st.warning("فعّل محركاً واحداً على الأقل.")
    else:
        cfg = {
            "num_results": num_results, "searx": searx_instance,
            "g_key": google_api_key, "g_cx": google_cx_id, "b_key": brave_api_key
        }
        
        with st.spinner("جاري استخراج البيانات... يرجى الانتظار (قد يستغرق 10-20 ثانية)"):
            start_time = time.time()
            res_map, err_map = run_all_tasks(search_username, cfg, enabled_engines)
            elapsed = time.time() - start_time
            
            st.session_state.res_map = res_map
            st.session_state.err_map = err_map
            st.session_state.elapsed = elapsed
            st.session_state.last_user = search_username

if "res_map" in st.session_state:
    res_map = st.session_state.res_map
    err_map = st.session_state.err_map
    
    all_results = []
    for items in res_map.values(): all_results.extend(items)
    
    st.success(f"انتهى البحث في {st.session_state.elapsed:.1f} ثانية. العثور على {len(all_results)} نتيجة.")
    
    # عرض الأخطاء إن وجدت ليعرف المستخدم سبب نقص النتائج
    if any(err_map.values()):
        with st.expander("⚠️ سجل الأخطاء والحظر (اضغط للتفاصيل)"):
            for eng, errs in err_map.items():
                if errs:
                    st.error(f"**{eng}:** " + " | ".join(errs))

    if not all_results:
        st.error("لم يتم العثور على أي نتائج. جميع المحركات إما حظرت الطلب أو اليوزر غير موجود في الأرشيف.")
    else:
        st.divider()
        for idx, r in enumerate(all_results, 1):
            with st.container(border=True):
                badge = ENGINE_BADGES.get(r["engine"], "🔹")
                st.markdown(f"**{idx}. {r['title']}** {badge} `{r['engine']}`")
                st.caption(f"🔗 [رابط النتيجة]({r['link']})")
                if r['snippet']:
                    st.write(r['snippet'])
