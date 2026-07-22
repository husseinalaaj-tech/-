import streamlit as st
import requests
import urllib.parse
import json
import io
import csv
import time
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from bs4 import BeautifulSoup
    _BS4_AVAILABLE = True
except ImportError:
    _BS4_AVAILABLE = False

# ==========================================
# 1. إعدادات الواجهة وتجربة المستخدم (UI/UX)
# ==========================================
st.set_page_config(
    page_title="Deep IG Comment Hunter",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .stTextInput input, .stSelectbox, .stMultiSelect {
        direction: ltr;
        text-align: left;
    }
    
    .result-card {
        background-color: #121212;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: transform 0.2s ease;
    }
    .result-card:hover {
        transform: translateX(-5px);
    }
    
    .highlight {
        background-color: #ff3d00;
        color: #fff;
        font-weight: bold;
        padding: 0 4px;
        border-radius: 3px;
    }
    
    .stats-box {
        background-color: #1e1e1e;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. البنية التحتية والاتصال (Core Architecture)
# ==========================================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_secure_session():
    """تهيئة جلسة اتصال معتمدة على آلية إعادة المحاولة لتجاوز التقطعات الشبكية"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }

def sanitize_username(username: str) -> str:
    """تنظيف المدخلات أمنياً والسماح فقط برموز إنستغرام الصالحة"""
    return re.sub(r'[^a-zA-Z0-9_.]', '', username.strip())

def generate_deep_dorks(username: str):
    """توليد صيغ بحث صارمة ومغلفة بعلامات التنصيص للإجبار على التطابق"""
    u = f'"{username}"'
    return [
        f'site:instagram.com/p/ {u}',
        f'site:instagram.com/reel/ {u}',
        f'site:instagram.com {u} "comments"',
        f'intext:"@{username}" site:instagram.com'
    ]

# ==========================================
# 3. طبقة الفلترة الصارمة (Strict Match Layer)
# ==========================================
def strict_exact_match_filter(results, username):
    """
    فلترة قاسية: لا تقبل النتيجة إلا إذا كان اليوزر موجوداً كنص مستقل.
    يستخدم Negative Lookbehind & Lookahead لضمان عدم ارتباط اليوزر بحروف أخرى.
    """
    safe_user = re.escape(username)
    # القواعد: اليوزر يجب أن يكون محاطاً ببداية/نهاية النص أو رموز غير تابعة لإنستغرام (مسافات، أقواس، الخ)
    pattern = re.compile(rf'(?:^|[^a-zA-Z0-9_.])({safe_user})(?:[^a-zA-Z0-9_.]|$)', re.IGNORECASE)
    
    filtered_results = []
    seen_links = set()
    
    for r in results:
        link = r['link']
        if link in seen_links:
            continue
            
        text_to_search = f"{r['title']} {r['snippet']} {urllib.parse.unquote(link)}"
        if pattern.search(text_to_search):
            filtered_results.append(r)
            seen_links.add(link)
            
    return filtered_results

# ==========================================
# 4. محركات البحث المتقدمة (Deep Search Modules)
# ==========================================
class DeepOSINTEngines:
    @staticmethod
    def yahoo_deep_search(session, username, pages=3):
        results, errors = [], []
        if not _BS4_AVAILABLE: return results, ["BeautifulSoup missing"]
        
        dorks = generate_deep_dorks(username)
        
        def fetch_page(q, page_num):
            page_results = []
            try:
                b_param = (page_num - 1) * 10 + 1 # Yahoo pagination logic: b=1, 11, 21
                url = f"https://search.yahoo.com/search?p={urllib.parse.quote(q)}&n=10&b={b_param}"
                resp = session.get(url, headers=get_random_headers(), timeout=12)
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for div in soup.find_all("div", class_="compTitle"):
                        a_tag = div.find("a")
                        desc_div = div.find_next_sibling("div", class_="compText")
                        if a_tag and "href" in a_tag.attrs:
                            page_results.append({
                                "engine": "Yahoo Deep",
                                "title": a_tag.text.strip(),
                                "link": a_tag["href"],
                                "snippet": desc_div.text.strip() if desc_div else ""
                            })
                elif resp.status_code == 429:
                    errors.append("Yahoo Rate Limit (429)")
            except Exception as e:
                errors.append(f"Yahoo Error: {str(e)}")
            return page_results

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for q in dorks:
                for p in range(1, pages + 1):
                    futures.append(executor.submit(fetch_page, q, p))
            
            for f in as_completed(futures):
                results.extend(f.result())
                time.sleep(random.uniform(0.1, 0.4)) # Jitter لمنع الحظر

        return results, errors

    @staticmethod
    def google_api_deep(session, username, api_key, cx_id, pages=3):
        results, errors = [], []
        if not api_key or not cx_id: return results, []
        
        dorks = generate_deep_dorks(username)
        
        def fetch_google_page(q, start_index):
            page_results = []
            try:
                params = {"q": q, "key": api_key, "cx": cx_id, "start": start_index, "num": 10}
                resp = session.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
                if resp.status_code == 200:
                    for item in resp.json().get("items", []):
                        page_results.append({
                            "engine": "Google API",
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", "")
                        })
            except Exception as e:
                pass
            return page_results

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for q in dorks:
                for p in range(pages):
                    start_idx = (p * 10) + 1 # Google pagination: start=1, 11, 21
                    futures.append(executor.submit(fetch_google_page, q, start_idx))
                    
            for f in as_completed(futures):
                results.extend(f.result())

        return results, errors

# ==========================================
# 5. واجهة المستخدم والتنفيذ
# ==========================================
st.title("🎯 Deep IG Comment Hunter (Exact Match)")
st.markdown("نظام استقصاء عميق يغوص في صفحات متعددة ويطبق فلترة صارمة لا تقبل إلا التطابق الحرفي التام لليوزر.")

with st.sidebar:
    st.header("⚙️ إعدادات المعمارية")
    search_depth = st.slider("عمق البحث (عدد الصفحات لكل صيغة)", 1, 5, 3, help="زيادة العمق تجلب نتائج أكثر لكنها تستغرق وقتاً أطول.")
    
    st.divider()
    use_yahoo = st.checkbox("🟣 Yahoo Deep Search (مجاني)", value=True)
    
    st.divider()
    st.subheader("محركات احترافية (API)")
    g_key = st.text_input("Google API Key", type="password")
    g_cx = st.text_input("Google CX ID", type="password")

col1, col2 = st.columns([3, 1])
with col1:
    target_user = st.text_input("أدخل يوزر الحساب المستهدف (تطابق تام):", placeholder="مثال: cristiano")
with col2:
    st.write("")
    st.write("")
    start_btn = st.button("🚀 بدء الاستخراج العميق", use_container_width=True, type="primary")

if start_btn:
    clean_user = sanitize_username(target_user)
    if not clean_user:
        st.error("يرجى إدخال اسم مستخدم صحيح.")
    elif not (use_yahoo or (g_key and g_cx)):
        st.warning("يرجى تفعيل محرك بحث واحد على الأقل.")
    else:
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        start_time = time.time()
        session = get_secure_session()
        raw_results, all_errors = [], []
        
        progress_text.text("جاري استخراج البيانات الخام من الصفحات العميقة...")
        progress_bar.progress(30)
        
        # تنفيذ الاستخراج المتوازي
        if use_yahoo:
            res, err = DeepOSINTEngines.yahoo_deep_search(session, clean_user, search_depth)
            raw_results.extend(res)
            all_errors.extend(err)
            
        progress_bar.progress(60)
        
        if g_key and g_cx:
            res, err = DeepOSINTEngines.google_api_deep(session, clean_user, g_key, g_cx, search_depth)
            raw_results.extend(res)
            all_errors.extend(err)
            
        progress_bar.progress(85)
        progress_text.text("جاري تطبيق خوارزمية التطابق الصارم (Strict Filtering)...")
        
        # تطبيق الفلترة الصارمة
        final_results = strict_exact_match_filter(raw_results, clean_user)
        
        progress_bar.progress(100)
        progress_text.empty()
        
        exec_time = time.time() - start_time
        
        # --- الإحصائيات (Data Presentation) ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.markdown(f'<div class="stats-box">📊 الروابط المسحوبة كلياً<br><h3>{len(raw_results)}</h3></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="stats-box">🎯 بعد التطابق الصارم<br><h3 style="color:#4CAF50;">{len(final_results)}</h3></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="stats-box">⏱️ زمن التنفيذ<br><h3>{exec_time:.1f} ث</h3></div>', unsafe_allow_html=True)

        if all_errors:
            with st.expander("⚠️ سجل الأخطاء والحظر المخفي"):
                for e in set(all_errors): st.caption(e)

        if not final_results:
            st.error(f"تم سحب {len(raw_results)} نتيجة محتملة، لكن خوارزمية التطابق الصارم استبعدتها جميعاً لعدم وجود اليوزر '{clean_user}' نصاً وحرفياً.")
        else:
            st.subheader(f"📋 النتائج المؤكدة لاحتوائها على اليوزر ({clean_user}):")
            
            # تمييز اليوزر بلون بارز باستخدام نفس الـ Regex الصارم
            highlight_pattern = re.compile(rf'(?:^|[^a-zA-Z0-9_.])({re.escape(clean_user)})(?:[^a-zA-Z0-9_.]|$)', re.IGNORECASE)
            
            for idx, r in enumerate(final_results, 1):
                # التمييز ضمن المقتطف
                display_snippet = r['snippet']
                if highlight_pattern.search(display_snippet):
                    display_snippet = highlight_pattern.sub(r' <span class="highlight">\1</span> ', display_snippet)
                else:
                    # إذا كان التطابق في العنوان أو الرابط فقط
                    display_snippet = f"<span style='color:#888;'>[اليوزر موجود في الرابط أو العنوان]</span> {display_snippet}"

                st.markdown(f"""
                <div class="result-card">
                    <h5 style="margin: 0 0 10px 0; color: #4CAF50;">{idx}. {r['engine']} - {r['title']}</h5>
                    <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 1.6;">{display_snippet}</p>
                    <a href="{r['link']}" target="_blank" style="color: #64B5F6; text-decoration: none; font-size: 13px;">🔗 رابط المنشور</a>
                </div>
                """, unsafe_allow_html=True)
                
            # التصدير
            st.divider()
            csv_buffer = io.StringIO()
            writer = csv.DictWriter(csv_buffer, fieldnames=["engine", "title", "snippet", "link"])
            writer.writeheader()
            writer.writerows(final_results)
            
            st.download_button(
                label="💾 تصدير النتائج الصارمة (CSV)",
                data=csv_buffer.getvalue().encode('utf-8-sig'),
                file_name=f"strict_comments_{clean_user}.csv",
                mime="text/csv",
                use_container_width=True
            )
