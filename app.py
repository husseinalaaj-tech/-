import streamlit as st
import urllib.parse
import requests
import re

# ---------------------------------------------------------
# 1. Page Configuration & UI Settings
# ---------------------------------------------------------
st.set_page_config(
    page_title="IG OSINT Dork Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, mobile-responsive UI (optimized for Safari/iOS)
st.markdown("""
<style>
    .dork-card {
        border: 1px solid #4B4B4B;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: #1E1E1E;
    }
    .dork-title {
        color: #E1306C;
        font-weight: bold;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .dork-desc {
        font-size: 0.9rem;
        color: #CCCCCC;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Sidebar: API Settings
# ---------------------------------------------------------
st.sidebar.header("⚙️ Search API Settings (Optional)")
st.sidebar.markdown("قم بتفعيل هذا الخيار لجلب النتائج مباشرة داخل التطبيق عبر واجهة برمجة تطبيقات Google.")

api_enabled = st.sidebar.toggle("تفعيل جلب النتائج المباشرة (Live Fetch)", value=False)
google_api_key = st.sidebar.text_input("Google API Key", type="password", disabled=not api_enabled)
google_cx_id = st.sidebar.text_input("Search Engine ID (CX)", type="password", disabled=not api_enabled)

st.sidebar.divider()
st.sidebar.caption("💡 **تنويه أمني:** هذه الأداة لا تقوم باختراق الحسابات، بل تعتمد حصرياً على البيانات المتاحة للعموم والمؤرشفة مسبقاً في محرك بحث Google.")

# ---------------------------------------------------------
# 3. Main Interface & Logic
# ---------------------------------------------------------
st.title("🎯 IG OSINT Dorks Generator")
st.markdown("""
تُستخدم هذه الأداة لتوليد استعلامات بحث متقدمة (Google Dorks) بهدف تتبع البصمة الرقمية العامة لحسابات إنستجرام. 
قم بإدخال اسم المستخدم، وسيقوم النظام بتوليد الروابط للبحث عن التعليقات، الإشارات، والملف الشخصي في الأماكن التي أرشفها محرك البحث.
""")

st.warning("⚠️ **تنويه تقني وواقعي:** نتائج هذا البحث تعتمد على ما تمكنت عناكب Google من فهرسته. الكثير من تعليقات إنستجرام تتطلب تسجيل الدخول ولا تظهر في محركات البحث.")

# Input sanitization
raw_user = st.text_input("👤 أدخل اسم المستخدم (Target Username):", placeholder="مثال: cristiano")

if raw_user:
    # Sanitize input: Strip '@', remove spaces, and keep only valid IG username chars
    clean_user = re.sub(r'[^a-zA-Z0-9_.]', '', raw_user.strip().lstrip('@'))
    
    if not clean_user:
        st.error("الرجاء إدخال اسم مستخدم صالح.")
    else:
        st.success(f"تم تنظيف المدخل: **{clean_user}** - جاري إنشاء الاستعلامات...")
        
        # ---------------------------------------------------------
        # 4. Dork Categories & Definitions
        # ---------------------------------------------------------
        dorks_data = [
            {
                "id": "comments",
                "title": "💬 1. التعليقات على منشورات الآخرين (Comments on External Posts)",
                "desc": "يبحث عن اسم المستخدم في روابط المنشورات العامة (Photos/Posts) التي لا تعود للحساب نفسه.",
                "dork": f'site:instagram.com/p/ "{clean_user}" -inurl:{clean_user}'
            },
            {
                "id": "reels",
                "title": "🎬 2. التفاعلات في مقاطع الريلز (Reels Interactions)",
                "desc": "يبحث عن الإشارات أو التعليقات الخاصة بالمستخدم في روابط مقاطع الريلز العامة.",
                "dork": f'site:instagram.com/reel/ "{clean_user}" -inurl:{clean_user}'
            },
            {
                "id": "mentions",
                "title": "🔗 3. الإشارات العامة (General Public Mentions)",
                "desc": "بحث عام عن أي ذكر لاسم المستخدم في كامل منصة إنستجرام، مع استبعاد ملفه الشخصي المباشر.",
                "dork": f'site:instagram.com "{clean_user}" -inurl:{clean_user}'
            },
            {
                "id": "profile",
                "title": "👤 4. فهرسة الملف الشخصي (Profile & Bio Indexing)",
                "desc": "يجبر محرك البحث على إظهار النسخة المؤرشفة من الملف الشخصي (للبحث في البايو أو الاسم).",
                "dork": f'site:instagram.com/{clean_user}'
            }
        ]

        # ---------------------------------------------------------
        # 5. Core Search Functionality
        # ---------------------------------------------------------
        def fetch_live_snippets(query, api_key, cx_id):
            """يستعلم من Google Custom Search API ويعالج الأخطاء بدقة."""
            try:
                url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={api_key}&cx={cx_id}"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", []), None
                elif response.status_code == 403:
                    return None, "خطأ 403: مفتاح API غير صالح أو تجاوزت الحد المسموح (Quota limits)."
                elif response.status_code == 400:
                    return None, "خطأ 400: معرف محرك البحث (CX) أو المفتاح غير صحيح."
                else:
                    return None, f"فشل الاتصال بـ API. كود الخطأ: {response.status_code}"
            
            except requests.exceptions.RequestException as e:
                return None, f"خطأ في الاتصال بالشبكة: {str(e)}"

        # ---------------------------------------------------------
        # 6. Render Results UI
        # ---------------------------------------------------------
        for index, item in enumerate(dorks_data):
            encoded_query = urllib.parse.quote(item["dork"])
            google_search_url = f"https://www.google.com/search?q={encoded_query}"
            
            # Using Streamlit Native Container
            with st.container():
                st.markdown(f"""
                <div class="dork-card">
                    <div class="dork-title">{item['title']}</div>
                    <div class="dork-desc">{item['desc']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                st.code(item["dork"], language="text")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.link_button("🌐 فتح في Google", url=google_search_url, use_container_width=True)
                
                with col2:
                    if api_enabled:
                        if st.button("📡 جلب النتائج المباشرة (Live Fetch)", key=f"fetch_btn_{index}", use_container_width=True):
                            if not google_api_key or not google_cx_id:
                                st.error("يرجى إدخال Google API Key و CX ID في القائمة الجانبية أولاً.")
                            else:
                                with st.spinner("جاري جلب البيانات من محرك البحث..."):
                                    results, error = fetch_live_snippets(item["dork"], google_api_key, google_cx_id)
                                    
                                    if error:
                                        st.error(error)
                                    elif not results:
                                        st.info("لم يتم العثور على أي نتائج لهذا الاستعلام.")
                                    else:
                                        st.success(f"تم العثور على {len(results)} نتائج.")
                                        for res in results:
                                            with st.expander(res.get("title", "نتيجة بدون عنوان")):
                                                st.caption(f"🔗 {res.get('link')}")
                                                st.write(res.get("snippet", "لا يوجد مقتطف نصي."))
                
                st.divider()

# ---------------------------------------------------------
# 7. Deployment Instructions
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 🚀 إرشادات النشر على Streamlit Cloud")
st.markdown("""
1. أنشئ ملفاً باسم `requirements.txt` في نفس المجلد الذي يحتوي على هذا الكود، وأضف بداخله مكتبة واحدة فقط: `requests`. (مكتبة Streamlit مثبتة مسبقاً في بيئة العمل).
2. ارفع كلا الملفين (`app.py` و `requirements.txt`) إلى مستودع GitHub الخاص بك.
3. توجه إلى [Streamlit Community Cloud](https://share.streamlit.io/)، وقم بربط المستودع الخاص بك واضغط على **Deploy**.
""")
