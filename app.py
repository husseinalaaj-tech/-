import streamlit as st
import urllib.parse
import requests
import re

# ---------------------------------------------------------
# 1. Page Configuration & UI Settings
# ---------------------------------------------------------
st.set_page_config(
    page_title="IG OSINT Comment & Snippet Extractor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .result-card {
        border: 1px solid #4B4B4B;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        background-color: #1E1E1E;
    }
    .result-title {
        color: #E1306C;
        font-weight: bold;
        font-size: 1.05rem;
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Sidebar: API Settings & Validator
# ---------------------------------------------------------
st.sidebar.header("⚙️ إعدادات وفحص مفاتيح Google API")
st.sidebar.markdown("أدخل مفاتيحك لاختبار اتصالها وجلب المقتطفات النصية المتاحة مباشرة.")

api_enabled = st.sidebar.toggle("تفعيل الجلب المباشر للمقتطفات", value=True)
google_api_key = st.sidebar.text_input("Google API Key", type="password", disabled=not api_enabled)
google_cx_id = st.sidebar.text_input("Search Engine ID (CX)", value="4048e706292bc447b", type="default", disabled=not api_enabled)

# زر فحص المفاتيح وتأكيد صلاحيتها
if api_enabled and st.sidebar.button("🔍 فحص صلاحية المفاتيح"):
    if not google_api_key or not google_cx_id:
        st.sidebar.error("يرجى إدخال المفتاح ومعرف المحرك أولاً.")
    else:
        with st.spinner("جاري اختبار الاتصال مع جوجل..."):
            try:
                test_url = f"https://www.googleapis.com/customsearch/v1?q=test&key={google_api_key}&cx={google_cx_id}"
                test_resp = requests.get(test_url, timeout=5)
                if test_resp.status_code == 200:
                    st.sidebar.success("✅ المفاتيح تعمل بشكل صحيح 100%!")
                elif test_resp.status_code == 403:
                    st.sidebar.error("❌ خطأ 403: المفتاح غير صالح أو تجاوز الحد المسموح.")
                elif test_resp.status_code == 400:
                    st.sidebar.error("❌ خطأ 400: معرف المحرك (CX) أو المفتاح خاطئ.")
                else:
                    st.sidebar.warning(f"⚠️ رمز الاستجابة: {test_resp.status_code}")
            except Exception as e:
                st.sidebar.error(f"❌ فشل الاتصال بالشبكة: {e}")

st.sidebar.divider()
st.sidebar.caption("💡 ملاحظة: مقتطفات النصوص تظهر بناءً على ما أرشفته جوجل في نتائج البحث العامة.")

# ---------------------------------------------------------
# 3. Main Interface
# ---------------------------------------------------------
st.title("🔍 مستخرج المقتطفات والنقاط العامة لإنستجرام")
st.markdown("""
تتيح لك هذه الأداة البحث عن البصمة الرقمية لحسابات إنستجرام واستخراج المقتطفات النصية المرتبطة بها مباشرة دون الحاجة لفتح كل رابط يدوياً.
""")

raw_user = st.text_input("👤 أدخل اسم المستخدم (Target Username):", placeholder="مثال: cristiano")

if raw_user:
    clean_user = re.sub(r'[^a-zA-Z0-9_.]', '', raw_user.strip().lstrip('@'))
    
    if not clean_user:
        st.error("الرجاء إدخال اسم مستخدم صالح.")
    else:
        st.success(f"تم تنظيف المدخل والبدء بالبحث لـ: **{clean_user}**")
        
        # تعريف الاستعلامات المتقدمة
        queries = [
            {
                "title": "💬 المقتطفات المرتبطة بالمنشورات والتعليقات الظاهرة",
                "dork": f'site:instagram.com/p/ "{clean_user}" -inurl:{clean_user}'
            },
            {
                "title": "🎬 المقتطفات المرتبطة بمقاطع الريلز",
                "dork": f'site:instagram.com/reel/ "{clean_user}" -inurl:{clean_user}'
            },
            {
                "title": "🔗 الإشارات والمذكرات العامة في المنصة",
                "dork": f'site:instagram.com "{clean_user}" -inurl:{clean_user}'
            }
        ]

        def fetch_results(query, api_key, cx_id):
            try:
                url = f"https://www.googleapis.com/customsearch/v1?q={urllib.parse.quote(query)}&key={api_key}&cx={cx_id}"
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    return resp.json().get("items", []), None
                else:
                    return None, f"كود الخطأ: {resp.status_code}"
            except Exception as e:
                return None, str(e)

        # تنفيذ البحث وعرض النتائج مباشرة
        for idx, item in enumerate(queries):
            st.markdown(f"### {item['title']}")
            st.code(item['dork'], language="text")
            
            if api_enabled and google_api_key and google_cx_id:
                results, err = fetch_results(item['dork'], google_api_key, google_cx_id)
                if err:
                    st.error(f"تعذر الجلب المباشر: {err}")
                elif not results:
                    st.info("لم يتم العثور على مقتطفات نصية لهذا الاستعلام حالياً.")
                else:
                    for res in results:
                        with st.container():
                            st.markdown(f"""
                            <div class="result-card">
                                <div class="result-title">{res.get('title', 'بدون عنوان')}</div>
                                <p style='font-size:0.95rem; color:#E0E0E0;'><b>النص المستخرج/المقتطف:</b> {res.get('snippet', 'لا يوجد نص.')}</p>
                                <a href="{res.get('link')}" target="_blank" style='font-size:0.85rem; color:#E1306C;'>🔗 رابط المصدر المباشر</a>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.info("قم بإفعيل مفاتيح API وإدخالها في القائمة الجانبية لعرض المقتطفات النصية هنا تلقائياً.")
            
            st.divider()
