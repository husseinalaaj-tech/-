import streamlit as st
import requests
import urllib.parse

# ---------------------------------------------------------
# 1. إعدادات الصفحة والواجهة
# ---------------------------------------------------------
st.set_page_config(
    page_title="Multi-Engine Archive & Search Extractor",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 أداة البحث المجمع واستخراج النصوص والأرشيف")
st.markdown("تطبيق مجمع لاستعلام محركات البحث والأرشيفات القانونية وجلب المقتطفات النصية مباشرة.")

# ---------------------------------------------------------
# 2. القائمة الجانبية لإدارة مفاتيح API
# ---------------------------------------------------------
st.sidebar.header("🔑 مفاتيح الوصول (APIs)")
st.sidebar.caption("أدخل المفاتيح الخاصة بالمحركات التي تريد تفعيلها:")

google_api_key = st.sidebar.text_input("Google API Key", type="password")
google_cx_id = st.sidebar.text_input("Google Custom Search (CX ID)", type="password")
bing_api_key = st.sidebar.text_input("Bing Search API Key", type="password")
brave_api_key = st.sidebar.text_input("Brave Search API Key", type="password")

# ---------------------------------------------------------
# 3. دوال الاستعلام الخاصة بكل محرك (Modular Engine Functions)
# ---------------------------------------------------------

def fetch_google_results(query, api_key, cx_id):
    """استعلام محرك Google Custom Search"""
    results = []
    if not api_key or not cx_id:
        return results
    try:
        exact_query = f'"{query.strip(\'"\')}"'
        url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(exact_query)}&key={api_key}&cx={cx_id}"
        resp = requests.get(url, timeout=10)
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
    except Exception as e:
        st.error(f"خطأ في الاتصال بـ Google: {e}")
    return results

def fetch_bing_results(query, api_key):
    """استعلام محرك Bing Web Search API"""
    results = []
    if not api_key:
        return results
    try:
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        params = {"q": f'"{query.strip(\'"\')}"', "textDecorations": False, "textFormat": "RAW"}
        url = "https://api.bing.microsoft.com/v7.0/search"
        resp = requests.get(url, headers=headers, params=params, timeout=10)
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
    except Exception as e:
        st.error(f"خطأ في الاتصال بـ Bing: {e}")
    return results

def fetch_wayback_results(query):
    """استعلام أرشيف الإنترنت Wayback Machine (لا يتطلب مفتاح API)"""
    results = []
    try:
        url = f"http://web.archive.org/cdx/search/cdx?url=*{urllib.parse.quote(query)}*&output=json&limit=10"
        resp = requests.get(url, timeout=10)
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
    except Exception:
        pass
    return results

# ---------------------------------------------------------
# 4. واجهة البحث والعرض
# ---------------------------------------------------------
search_query = st.text_input("أدخل النص أو الكلمة الحرفية المراد البحث عنها عبر المحركات:", placeholder='مثال: "نص التعليق المطلوب"')

if st.button("تشغيل البحث المجمع", type="primary"):
    if not search_query.strip():
        st.warning("يرجى إدخال نص للبحث.")
    else:
        with st.spinner("جاري استعلام المحركات المحددة..."):
            google_data = fetch_google_results(search_query, google_api_key, google_cx_id)
            bing_data = fetch_bing_results(search_query, bing_api_key)
            wayback_data = fetch_wayback_results(search_query)

        # عرض النتائج في تبويبات منظمة
        tab_all, tab_google, tab_bing, tab_wayback = st.tabs([
            f"الكل ({len(google_data) + len(bing_data) + len(wayback_data)})",
            f"Google ({len(google_data)})",
            f"Bing ({len(bing_data)})",
            f"Wayback Archive ({len(wayback_data)})"
        ])

        def display_results_list(results):
            if not results:
                st.info("لا توجد نتائج متوفرة لهذا المحرك حاليًا (تحقق من إدخال مفاتيح الـ API الخاصة بالمحرك).")
                return
            for idx, item in enumerate(results, 1):
                with st.container():
                    st.markdown(f"**{idx}. {item['title']}** — `{item['engine']}`")
                    st.caption(f"المصدر: [{item['source']}]({item['link']})")
                    st.text_area("المقتطف النصي المستخرج:", value=item['snippet'], height=80, key=f"{item['engine']}_{idx}_{item['link']}")
                    st.divider()

        with tab_all:
            all_combined = google_data + bing_data + wayback_data
            display_results_list(all_combined)

        with tab_google:
            display_results_list(google_data)

        with tab_bing:
            display_results_list(bing_data)

        with tab_wayback:
            display_results_list(wayback_data)
