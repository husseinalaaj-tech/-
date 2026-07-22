import streamlit as st
import requests
import urllib.parse
import csv
import io
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="IG Footprint Tracker", page_icon="📸", layout="wide")

st.title("📸 رادار تعقب يوزرات إنستجرام (IG Footprint)")

# الإعدادات
st.sidebar.header("⚙️ الإعدادات")
no_key_mode = st.sidebar.toggle("🆓 وضع المحركات المجانية (بدون API)", value=True)

google_api_key = st.sidebar.text_input("Google API Key", type="password", disabled=no_key_mode)
google_cx_id = st.sidebar.text_input("Google CX ID", type="password", disabled=no_key_mode)
results_limit = st.sidebar.slider("عدد النتائج المطلوب", 5, 20, 10)

# ---------------------------------------------------------
# دوال جلب البيانات المصلحة
# ---------------------------------------------------------

def fetch_ddg_simple(username, limit):
    """استعلامات مبسطة ومباشرة لـ DuckDuckGo بدون تعقيد"""
    results = []
    u = username.strip().lstrip("@")
    queries = [
        f'site:instagram.com "{u}"',
        f'"{u}" instagram'
    ]
    
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for q in queries:
                for item in ddgs.text(q, max_results=limit):
                    results.append({
                        "engine": "DuckDuckGo",
                        "title": item.get("title", ""),
                        "source": item.get("href", ""),
                        "snippet": item.get("body", ""),
                        "link": item.get("href", "")
                    })
    except Exception:
        pass
    return results

def fetch_wayback_clean(username, limit):
    """استعلام مباشر للأرشيف بدون نجمة عشوائية"""
    results = []
    u = username.strip().lstrip("@")
    try:
        # طلب الصفحة المباشرة لبروفايل اليوزر
        url = f"https://web.archive.org/cdx/search/cdx?url=instagram.com/{u}/&output=json&limit={limit}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for row in data[1:]:
                    timestamp, orig_url = row[1], row[2]
                    results.append({
                        "engine": "Wayback Archive",
                        "title": f"لقطة مؤرشفة لبروفايل (@{u})",
                        "source": "instagram.com",
                        "snippet": f"تاريخ الأرشفة: {timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
                        "link": f"https://web.archive.org/web/{timestamp}/{orig_url}"
                    })
    except Exception:
        pass
    return results

def fetch_google_clean(username, key, cx, limit):
    results = []
    if not key or not cx: return results
    u = username.strip().lstrip("@")
    q = f'site:instagram.com "{u}"'
    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(q)}&key={key}&cx={cx}&num={min(limit, 10)}"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                results.append({
                    "engine": "Google",
                    "title": item.get("title"),
                    "source": item.get("displayLink"),
                    "snippet": item.get("snippet"),
                    "link": item.get("link")
                })
    except Exception:
        pass
    return results

# ---------------------------------------------------------
# الواجهة والتشغيل
# ---------------------------------------------------------

ig_user = st.text_input("👤 أدخل يوزر إنستجرام المستهدف:", placeholder="مثال: cristiano")

if st.button("🔍 بدء التفتيش", type="primary", use_container_width=True):
    if not ig_user.strip():
        st.warning("يرجى إدخال اسم المستخدم.")
    else:
        start_time = time.time()
        clean_u = ig_user.strip().lstrip("@")
        
        with st.spinner(f"جاري التفتيش عن @{clean_u}..."):
            all_results = []
            
            # جلب نتائج DuckDuckGo والأرشيف
            ddg_res = fetch_ddg_simple(clean_u, results_limit)
            wb_res = fetch_wayback_clean(clean_u, results_limit)
            all_results.extend(ddg_res)
            all_results.extend(wb_res)
            
            # جلب جوجل إن كان مفعلاً
            if not no_key_mode:
                g_res = fetch_google_clean(clean_u, google_api_key, google_cx_id, results_limit)
                all_results.extend(g_res)

        elapsed = round(time.time() - start_time, 2)
        
        # إزالة التكرار بناءً على الروابط
        seen_links = set()
        unique_results = []
        for r in all_results:
            if r['link'] not in seen_links and r['link']:
                seen_links.add(r['link'])
                unique_results.append(r)

        if not unique_results:
            st.error(f"لم يتم العثور على نتائج لـ @{clean_u}. جرب البحث بدون الوضع المجاني أو التأكد من الاتصال.")
        else:
            st.success(f"تم العثور على {len(unique_results)} نتيجة في {elapsed} ثانية!")
            
            for item in unique_results:
                uid = uuid.uuid4().hex[:6]
                with st.container():
                    st.markdown(f"**{item['title']}** (`{item['engine']}`)")
                    if item['link']:
                        st.caption(f"🔗 [{item['link']}]({item['link']})")
                    st.text_area("النص:", value=item['snippet'], height=70, key=f"res_{uid}")
                    st.divider()
