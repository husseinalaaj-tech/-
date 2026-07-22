import streamlit as st
import requests
import urllib.parse
import json
import io
import csv
import time
import uuid
import re
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
    page_title="IG Comment Hunter | OSINT",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* تحسين توافقية اليمين لليسار (RTL) بشكل نظيف */
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
    
    html, body, [class*="css"]  {
        font-family: 'Tajawal', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .stTextInput input, .stSelectbox, .stMultiSelect {
        direction: ltr; /* للحفاظ على تنسيق اليوزر والروابط */
        text-align: left;
    }
    
    .result-card {
        background-color: #1E1E1E;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
        margin-bottom: 15px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .result-card:hover {
        border-color: #4CAF50;
        transform: translateY(-2px);
    }
    
    .highlight {
        background-color: #ffeb3b;
        color: #000;
        font-weight: bold;
        padding: 0 4px;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. البنية التحتية والاتصال (Core Architecture)
# ==========================================
def get_secure_session():
    """تهيئة جلسة اتصال معتمدة على آلية إعادة المحاولة لتجاوز التقطعات الشبكية"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    })
    return session

def sanitize_username(username: str) -> str:
    """تنظيف المدخلات أمنياً"""
    return re.sub(r'[^a-zA-Z0-9_.]', '', username.strip())

def generate_comment_dorks(username: str):
    """توليد صيغ بحث مخصصة لاصطياد التعليقات والإشارات فقط"""
    u = username
    return [
        f'site:instagram.com/p/ intext:"@{u}"',            # الإشارة إليه في تعليق/منشور
        f'site:instagram.com/reel/ intext:"@{u}"',         # الإشارة في ريلز
        f'site:instagram.com/tv/ intext:"@{u}"',           # IGTV القديمة
        f'"{u}" site:instagram.com/p/ "comments"',         # ظهوره في صفحة تحتوي كلمة تعليقات
        f'inurl:instagram.com/p/ "{u}"'                    # تواجد اسمه نصياً داخل روابط المنشورات
    ]

# ==========================================
# 3. محركات البحث (Search Modules)
# ==========================================
class OSINTEngines:
    @staticmethod
    def duckduckgo_lite(session, username, num_results):
        results, errors = [], []
        if not _BS4_AVAILABLE: return results, ["BeautifulSoup missing"]
        
        for q in generate_comment_dorks(username):
            try:
                resp = session.post("https://lite.duckduckgo.com/lite/", data={"q": q, "kl": "wt-wt"}, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for tr in soup.find_all("tr"):
                        a_tag = tr.find("a", class_="result-url")
                        snippet_td = tr.find("td", class_="result-snippet")
                        if a_tag and "instagram.com" in a_tag.get("href", ""):
                            results.append({
                                "engine": "DuckDuckGo",
                                "title": a_tag.text.strip(),
                                "link": a_tag["href"],
                                "snippet": snippet_td.text.strip() if snippet_td else "لا يوجد وصف"
                            })
            except Exception as e:
                errors.append(f"DDG Error: {str(e)}")
        return results, errors

    @staticmethod
    def yahoo_search(session, username, num_results):
        results, errors = [], []
        if not _BS4_AVAILABLE: return results, ["BeautifulSoup missing"]
        
        for q in generate_comment_dorks(username):
            try:
                url = f"https://search.yahoo.com/search?p={urllib.parse.quote(q)}&n={num_results}"
                resp = session.get(url, timeout=10)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for div in soup.find_all("div", class_="compTitle"):
                        a_tag = div.find("a")
                        desc_div = div.find_next_sibling("div", class_="compText")
                        if a_tag and "href" in a_tag.attrs:
                            results.append({
                                "engine": "Yahoo Search",
                                "title": a_tag.text.strip(),
                                "link": a_tag["href"],
                                "snippet": desc_div.text.strip() if desc_div else "تفاصيل التعليق مخفية"
                            })
            except Exception as e:
                errors.append(f"Yahoo Error: {str(e)}")
        return results, errors

    @staticmethod
    def google_api(session, username, api_key, cx_id, num_results):
        results, errors = [], []
        if not api_key or not cx_id: return results, []
        
        for q in generate_comment_dorks(username):
            try:
                params = {"q": q, "key": api_key, "cx": cx_id, "num": min(num_results, 10)}
                resp = session.get("https://www.googleapis.com/customsearch/v1", params=params, timeout=10)
                if resp.status_code == 200:
                    for item in resp.json().get("items", []):
                        results.append({
                            "engine": "Google API",
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", "")
                        })
                else:
                    errors.append(f"Google API: {resp.status_code}")
            except Exception as e:
                errors.append(f"Google Error: {str(e)}")
        return results, errors

def deduplicate_results(results):
    """إزالة النتائج المكررة بناءً على الرابط بدقة O(N)"""
    seen = set()
    return [r for r in results if not (r["link"] in seen or seen.add(r["link"]))]

# ==========================================
# 4. بناء واجهة المستخدم وإدارة العمليات
# ==========================================
st.title("🎯 Instagram Comments Hunter")
st.markdown("أداة متقدمة مصممة معمارياً للبحث عن **تعليقات أو إشارات (Mentions)** لحساب إنستغرام محدد داخل المنشورات، باستخدام صيغ بحث موجهة.")

# --- القائمة الجانبية ---
with st.sidebar:
    st.header("⚙️ إعدادات المحركات")
    num_req = st.slider("عمق البحث لكل صيغة", 5, 20, 10)
    
    st.divider()
    st.subheader("محركات مجانية")
    use_ddg = st.checkbox("🦆 DuckDuckGo", value=True)
    use_yahoo = st.checkbox("🟣 Yahoo Search", value=True)
    
    st.divider()
    st.subheader("محركات احترافية (API)")
    st.caption("تعطي أدق النتائج للتعليقات.")
    g_key = st.text_input("Google API Key", type="password")
    g_cx = st.text_input("Google CX ID", type="password")

# --- محرك البحث الرئيسي ---
col1, col2 = st.columns([3, 1])
with col1:
    target_user = st.text_input("أدخل يوزر الحساب المستهدف:", placeholder="مثال: cristiano")
with col2:
    st.write("")
    st.write("")
    start_btn = st.button("🔍 استخراج التعليقات", use_container_width=True, type="primary")

if start_btn:
    clean_user = sanitize_username(target_user)
    if not clean_user:
        st.error("يرجى إدخال اسم مستخدم صحيح (أحرف إنجليزية، أرقام، وشرطة سفلية فقط).")
    elif not (use_ddg or use_yahoo or (g_key and g_cx)):
        st.warning("يرجى تفعيل محرك بحث واحد على الأقل أو إدخال مفاتيح Google.")
    else:
        with st.spinner("جاري مسح قواعد البيانات وفلترة روابط المنشورات..."):
            session = get_secure_session()
            tasks = {}
            
            if use_ddg: tasks["DDG"] = lambda: OSINTEngines.duckduckgo_lite(session, clean_user, num_req)
            if use_yahoo: tasks["Yahoo"] = lambda: OSINTEngines.yahoo_search(session, clean_user, num_req)
            if g_key and g_cx: tasks["Google"] = lambda: OSINTEngines.google_api(session, clean_user, g_key, g_cx, num_req)

            all_results, all_errors = [], []
            start_time = time.time()
            
            # التنفيذ المتوازي المدار
            with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
                future_to_name = {executor.submit(func): name for name, func in tasks.items()}
                for future in as_completed(future_to_name):
                    res, errs = future.result()
                    all_results.extend(res)
                    all_errors.extend(errs)

            final_results = deduplicate_results(all_results)
            exec_time = time.time() - start_time

            # --- عرض النتائج (Data Presentation) ---
            st.divider()
            
            metrics_cols = st.columns(3)
            metrics_cols[0].metric("الروابط المحتملة للتعليقات", len(final_results))
            metrics_cols[1].metric("زمن الاستجابة", f"{exec_time:.2f} ثانية")
            metrics_cols[2].metric("حالة النظام", "مستقر" if not all_errors else "توجد تحذيرات")

            if all_errors:
                with st.expander("⚠️ سجل أخطاء الشبكة / الحظر"):
                    for e in set(all_errors): st.write(f"- {e}")

            if not final_results:
                st.info(f"لم يتم العثور على آثار تعليقات أو إشارات للحساب '{clean_user}'. (قد يكون الحساب خاصاً أو لم يتم أرشفة تعليقاته).")
            else:
                st.subheader("📋 المنشورات التي يُحتمل وجود تعليق أو إشارة للمستخدم بها:")
                
                # إبراز اسم المستخدم في النتائج
                highlight_pattern = re.compile(f'({re.escape(clean_user)})', re.IGNORECASE)
                
                for idx, r in enumerate(final_results, 1):
                    # تطبيق التمييز اللوني على النص
                    highlighted_snippet = highlight_pattern.sub(r'<span class="highlight">\1</span>', r['snippet'])
                    
                    st.markdown(f"""
                    <div class="result-card">
                        <h4 style="margin: 0 0 10px 0; color: #4CAF50;">
                            {idx}. {r['engine']}
                        </h4>
                        <p style="margin: 0 0 10px 0; font-size: 14px;">
                            {highlighted_snippet}
                        </p>
                        <a href="{r['link']}" target="_blank" style="color: #64B5F6; text-decoration: none; font-size: 13px;">
                            🔗 الانتقال إلى المنشور لقراءة التعليق
                        </a>
                    </div>
                    """, unsafe_allow_html=True)
                    
                # التصدير (Export)
                st.divider()
                csv_buffer = io.StringIO()
                writer = csv.DictWriter(csv_buffer, fieldnames=["engine", "title", "snippet", "link"])
                writer.writeheader()
                writer.writerows(final_results)
                
                st.download_button(
                    label="💾 تصدير النتائج (CSV)",
                    data=csv_buffer.getvalue().encode('utf-8-sig'),
                    file_name=f"comments_{clean_user}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
