import streamlit as st
import requests
import urllib.parse
import csv
import io
import time
import uuid

st.set_page_config(page_title="Public Comments Extractor", page_icon="💬", layout="wide")

st.title("💬 باحث التعليقات والردود العامة (Public Comments Finder)")
st.markdown("يقوم هذا البرامج بالتفتيش في المنصات والمنتديات المفتوحة التي تجعل تعليقات المستخدمين مقتطعة ومؤرشفة علنًا.")

# ---------------------------------------------------------
# الإعدادات الجانبية
# ---------------------------------------------------------
st.sidebar.header("⚙️ الإعدادات")
results_limit = st.sidebar.slider("عدد التعليقات المطلوبة لكل منصة", 5, 25, 10)

# ---------------------------------------------------------
# دالة استخراج التعليقات الموجهة
# ---------------------------------------------------------
def search_public_comments(username, limit):
    """صياغة استعلامات موجهة خصيصاً لجلب التعليقات والردود النصية"""
    u = username.strip().lstrip("@")
    results = []
    
    # استعلامات تستهدف أنماط التعليقات والردود
    comment_targets = {
        "Reddit Comments": f'site:reddit.com/user/{u} OR (site:reddit.com "{u}" "comment")',
        "Disqus Network": f'site:disqus.com "{u}"',
        "المنتديات والمدونات": f'"{u}" ("commented" OR "replied" OR "كتب تعليقاً" OR "رد") -site:instagram.com -site:facebook.com'
    }
    
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for source_name, query in comment_targets.items():
                for item in ddgs.text(query, max_results=limit):
                    results.append({
                        "source": source_name,
                        "title": item.get("title", ""),
                        "snippet": item.get("body", ""),
                        "link": item.get("href", "")
                    })
    except Exception as e:
        st.error(f"حدث خطأ أثناء الاتصال بمحرك البحث: {e}")
        
    return results

# ---------------------------------------------------------
# الواجهة التشغيلية
# ---------------------------------------------------------
target_user = st.text_input("👤 أدخل اسم المستخدم (Username) للبحث عن تعليقاته:", placeholder="مثال: alex_99")

if st.button("🔍 استخراج التعليقات النصية", type="primary", use_container_width=True):
    if not target_user.strip():
        st.warning("يرجى إدخال اسم مستخدم أولاً.")
    else:
        clean_user = target_user.strip().lstrip("@")
        start_time = time.time()
        
        with st.spinner(f"جاري مسح المنصات العامة لاصطياد تعليقات @{clean_user}..."):
            raw_results = search_public_comments(clean_user, results_limit)
            
        elapsed = round(time.time() - start_time, 2)
        
        # تصفية النتائج والتأكد من عدم التكرار
        seen_links = set()
        filtered_comments = []
        for r in raw_results:
            if r['link'] not in seen_links and r['link']:
                seen_links.add(r['link'])
                filtered_comments.append(r)
                
        if not filtered_comments:
            st.info(f"لم يتم العثور على تعليقات نصية مؤرشفة علنًا باسم @{clean_user} في المنصات المفتوحة.")
        else:
            st.success(f"تم جلب {len(filtered_comments)} تعليق/مشاركة في {elapsed} ثانية!")
            
            # العرض
            for item in filtered_comments:
                uid = uuid.uuid4().hex[:6]
                with st.container():
                    st.markdown(f"**{item['title']}** — `{item['source']}`")
                    st.caption(f"🔗 [رابط الصفحة/التعليق]({item['link']})")
                    st.text_area("مقتطف التعليق النصي:", value=item['snippet'], height=85, key=f"comm_{uid}")
                    st.divider()
