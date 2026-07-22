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
# 1. إعدادات الصفحة والواجهة
# ---------------------------------------------------------
st.set_page_config(page_title="IG Footprint Tracker", page_icon="📸", layout="wide")

st.markdown("""
<style>
.result-card { border: 1px solid rgba(225,48,108,0.3); border-radius: 10px; padding: 14px; margin-bottom: 12px; background-color: rgba(225,48,108,0.03); border-right: 4px solid #E1306C; }
.result-title { font-size: 1.05rem; font-weight: bold; margin-bottom: 4px; color: #E1306C; }
.result-meta { font-size: 0.85rem; opacity: 0.8; margin-bottom: 6px; }
.engine-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: bold; background-color: rgba(225,48,108,0.1); color: #E1306C; margin-inline-start: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("📸 رادار تعقب يوزرات إنستجرام (IG Footprint OSINT)")
st.markdown("يقوم هذا الرادار بتركيز قوة محركات البحث والأرشيف لاصطياد أي أثر لليوزر (منشن، مواقع طرف ثالث، أرشيف قديم) مرتبط بإنستجرام.")

# ---------------------------------------------------------
# 2. القائمة الجانبية والمفاتيح
# ---------------------------------------------------------
st.sidebar.header("⚙️ إعدادات البحث")
no_key_mode = st.sidebar.toggle("🆓 وضع المحركات المجانية (بدون API)", value=True)

st.sidebar.divider()
google_api_key = st.sidebar.text_input("Google API Key", type="password", disabled=no_key_mode)
google_cx_id = st.sidebar.text_input("Google CX ID", type="password", disabled=no_key_mode)
bing_api_key = st.sidebar.text_input("Bing API Key", type="password", disabled=no_key_mode)

results_per_engine = st.sidebar.slider("عدد النتائج من كل محرك", 5, 30, 10)

# ---------------------------------------------------------
# 3. بناء استعلام إنستجرام الذكي (OSINT Dorks)
# ---------------------------------------------------------
def build_ig_query(username):
    """صياغة استعلام يجبر المحركات على البحث عن اليوزر في بيئة إنستجرام"""
    u = username.strip().lstrip("@")
    # استعلام مدمج: يبحث في إنستجرام، مواقع الطرف الثالث، أو أي رابط يحمل اسم اليوزر
    query = f'site:instagram.com "@{u}" OR "{u}" site:picuki.com OR "instagram.com/{u}"'
    return query, u

# ---------------------------------------------------------
# 4. دوال الاستعلام (Google, Bing, DuckDuckGo, Wayback)
# ---------------------------------------------------------
def fetch_google(query, key, cx, num):
    start = time.time()
    results = []
    if not key or not cx: return results, 0
    try:
        url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={key}&cx={cx}&num={min(num, 10)}"
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                results.append({"engine": "Google", "title": item.get("title"), "source": item.get("displayLink"), "snippet": item.get("snippet"), "link": item.get("link")})
    except Exception: pass
    return results, round(time.time() - start, 2)

def fetch_bing(query, key, num):
    start = time.time()
    results = []
    if not key: return results, 0
    try:
        headers = {"Ocp-Apim-Subscription-Key": key}
        params = {"q": query, "textDecorations": False, "count": num}
        resp = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params, timeout=12)
        if resp.status_code == 200:
            for page in resp.json().get("webPages", {}).get("value", []):
                results.append({"engine": "Bing", "title": page.get("name"), "source": page.get("displayUrl"), "snippet": page.get("snippet"), "link": page.get("url")})
    except Exception: pass
    return results, round(time.time() - start, 2)

def fetch_duckduckgo(query, num):
    start = time.time()
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=num):
                results.append({"engine": "DuckDuckGo", "title": item.get("title"), "source": item.get("href"), "snippet": item.get("body"), "link": item.get("href")})
    except ImportError:
        results.append({"engine": "DuckDuckGo", "title": "مكتبة مفقودة", "source": "", "snippet": "يرجى تثبيت duckduckgo-search", "link": ""})
    except Exception: pass
    return results, round(time.time() - start, 2)

def fetch_wayback_ig(username, num):
    """بحث مخصص لأرشيف صفحة الإنستجرام الخاصة باليوزر"""
    start = time.time()
    results = []
    try:
        target_url = f"instagram.com/{username}"
        url = f"https://web.archive.org/cdx/search/cdx?url=*{target_url}*&output=json&limit={num}&collapse=urlkey"
        resp = requests.get(url, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) > 1:
                for row in data[1:]:
                    timestamp, orig_url = row[1], row[2]
                    results.append({
                        "engine": "Wayback Archive",
                        "title": f"لقطة مؤرشفة لحساب أو منشور (@{username})",
                        "source": "instagram.com",
                        "snippet": f"التقطت هذه النسخة من الحساب/المنشور بتاريخ: {timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}",
                        "link": f"https://web.archive.org/web/{timestamp}/{orig_url}"
                    })
    except Exception: pass
    return results, round(time.time() - start, 2)

# ---------------------------------------------------------
# 5. الواجهة الأساسية والتشغيل المتوازي
# ---------------------------------------------------------
ig_username = st.text_input("👤 أدخل يوزر إنستجرام المستهدف:", placeholder="مثال: cristiano")

if st.button("🔍 بدء التفتيش الشامل لليوزر", type="primary", use_container_width=True):
    if not ig_username.strip():
        st.warning("يرجى إدخال اسم مستخدم (يوزر) للبحث عنه.")
    else:
        status_ph = st.empty()
        p_bar = st.progress(0)
        overall_start = time.time()
        
        target_query, clean_user = build_ig_query(ig_username)
        
        tasks = {}
        if not no_key_mode:
            tasks["Google"] = (fetch_google, (target_query, google_api_key, google_cx_id, results_per_engine))
            tasks["Bing"] = (fetch_bing, (target_query, bing_api_key, results_per_engine))
        tasks["DuckDuckGo"] = (fetch_duckduckgo, (target_query, results_per_engine))
        tasks["Wayback"] = (fetch_wayback_ig, (clean_user, results_per_engine))

        results_map = {name: [] for name in tasks}
        completed = 0
        total = len(tasks)

        with ThreadPoolExecutor(max_workers=max(total, 1)) as executor:
            future_to_name = {executor.submit(func, *args): name for name, (func, args) in tasks.items()}
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    res, _ = future.result()
                    results_map[name] = res
                except Exception: pass
                completed += 1
                p_bar.progress(completed / total)
                status_ph.markdown(f"✅ تم فحص **{name}**...")
                
        p_bar.empty()
        status_ph.success(f"انتهى الفحص في {round(time.time() - overall_start, 2)} ثانية.")

        # تجميع النتائج
        all_combined = sum(results_map.values(), [])
        
        if not all_combined:
            st.error(f"لم يتم العثور على أي أثر لليوزر @{clean_user} في المحركات المتاحة.")
        else:
            st.subheader(f"📊 النتائج المستخرجة لـ @{clean_user} ({len(all_combined)} نتيجة)")
            
            # أزرار التصدير
            def export_csv(data):
                out = io.StringIO()
                w = csv.DictWriter(out, fieldnames=["engine", "title", "source", "snippet", "link"])
                w.writeheader()
                for r in data: w.writerow(r)
                return out.getvalue().encode("utf-8-sig")
            
            st.download_button("⬇️ تصدير النتائج (CSV)", data=export_csv(all_combined), file_name=f"ig_{clean_user}_report.csv", mime="text/csv")
            st.divider()
            
            # العرض في بطاقات أنيقة
            for item in all_combined:
                uid = uuid.uuid4().hex[:6]
                with st.container():
                    st.markdown(
                        f"<div class='result-card'>"
                        f"<div class='result-title'>{item.get('title') or 'نتيجة بدون عنوان'}<span class='engine-badge'>{item.get('engine','')}</span></div>"
                        f"<div class='result-meta'>المصدر: {item.get('source','')}</div>"
                        f"</div>", unsafe_allow_html=True)
                    if item.get("link"): st.caption(f"🔗 [{item['link']}]({item['link']})")
                    st.text_area("النص المقتطع:", value=item.get("snippet") or "لا يوجد نص متوفر", height=75, key=f"snp_{uid}", label_visibility="collapsed")
                    st.write("") # Space
