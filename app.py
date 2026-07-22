import streamlit as st
import random

# إعدادات الصفحة
st.set_page_config(
    page_title="Random Key Generator",
    page_icon="🔑",
    layout="centered"
)

st.title("🔑 مولّد المفاتيح العشوائية")
st.markdown("أداة بسيطة لتوليد مفاتيح عشوائية بالصيغة المطلوبة مع استبعاد الحروف والأرقام المتشابهة (O, 0, I, 1, B, 8).")

def generate_random_key():
    # الحروف والأرقام المسموحة بعد الاستبعاد
    chars = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"
    
    def generate_segment():
        return "".join(random.choices(chars, k=5))
    
    segments = [generate_segment() for _ in range(5)]
    return "-".join(segments)

# زر لتوليد مفتاح جديد
if st.button("🎲 توليد مفتاح جديد", use_container_width=True):
    key = generate_random_key()
    st.success("تم التوليد بنجاح:")
    st.code(key, language="text")
else:
    # عرض مفتاح افتراضي عند فتح الصفحة أول مرة
    initial_key = generate_random_key()
    st.code(initial_key, language="text")
