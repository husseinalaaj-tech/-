import streamlit as st
import random

# إعدادات الصفحة
st.set_page_config(
    page_title="Continuous Key Generator",
    page_icon="⚡",
    layout="centered"
)

st.title("⚡ مولّد المفاتيح المستمر والسريع")
st.markdown("يقوم هذا السكربت بتوليد المفاتيح العشوائية بشكل متواصل بأقصى سرعة ممكنة مع احتساب الإجمالي.")

# الحروف والأرقام المسموحة بعد استبعاد (O, 0, I, 1, B, 8)
CHARS = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"

def generate_random_key():
    def generate_segment():
        return "".join(random.choices(CHARS, k=5))
    return "-".join([generate_segment() for _ in range(5)])

# تهيئة المتغيرات في الجلسة (Session State)
if "running" not in st.session_state:
    st.session_state.running = False
if "total_count" not in st.session_state:
    st.session_state.total_count = 0

# أزرار التحكم
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ بدء التوليد المستمر", use_container_width=True):
        st.session_state.running = True
with col2:
    if st.button("⏹️ إيقاف التوليد", use_container_width=True):
        st.session_state.running = False

# عناصر العرض المباشر
metric_container = st.empty()
text_container = st.empty()

# عملية التوليد المستمر
if st.session_state.running:
    keys_buffer = []
    
    # حلقة تكرار مستمرة بأقصى سرعة
    while st.session_state.running:
        # توليد دفعة مكونة من 100 مفتاح في كل تكرار لرفع السرعة لأقصى حد
        batch = [generate_random_key() for _ in range(100)]
        st.session_state.total_count += len(batch)
        
        # إضافة المفاتيح للذاكرة المؤقتة لآخر 500 مفتاح لمنع بطء المتصفح
        keys_buffer.extend(batch)
        if len(keys_buffer) > 500:
            keys_buffer = keys_buffer[-500:]
        
        # تحديث الواجهة فوراً
        metric_container.metric(
            label="📊 إجمالي المفاتيح المولدة حتى الآن:", 
            value=f"{st.session_state.total_count:,}"
        )
        text_container.text_area(
            label="القائمة الجارية (تتحدث باستمرار):", 
            value="\n".join(keys_buffer), 
            height=350
        )
else:
    metric_container.metric(
        label="📊 إجمالي المفاتيح المولدة حتى الآن:", 
        value=f"{st.session_state.total_count:,}"
    )
    text_container.info("اضغط على زر 'بدء التوليد المستمر' لتشغيل المحرك.")
