import streamlit as st
import random

# إعدادات الصفحة
st.set_page_config(
    page_title="Random Key Generator",
    page_icon="🔑",
    layout="centered"
)

st.title("🔑 مولّد المفاتيح العشوائية التلقائي")
st.markdown("يتم توليد مفاتيح عشوائية جديدة تلقائياً وفق القواعد المحددة.")

def generate_random_key():
    # الحروف والأرقام المسموحة بعد استبعاد المتشابهات
    chars = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"
    
    def generate_segment():
        return "".join(random.choices(chars, k=5))
    
    segments = [generate_segment() for _ in range(5)]
    return "-".join(segments)

# توليد مفتاح جديد مباشرة وبشكل تلقائي عند كل تحميل للصفحة
key = generate_random_key()

st.success("المفتاح المولّد:")
st.code(key, language="text")

# زر إضافي إذا أردت توليد مفتاح جديد يدوياً بالضغط
if st.button("🔄 تحديث / توليد مفتاح آخر", use_container_width=True):
    st.rerun()
