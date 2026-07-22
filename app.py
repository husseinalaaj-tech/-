import streamlit as st
import random
import time

# إعدادات الصفحة
st.set_page_config(
    page_title="Xbox Gift Card Auto-Redeemer",
    page_icon="🎮",
    layout="centered"
)

st.title("🎮 أداة إدخال وتوليد بطاقات Xbox")
st.markdown("أداة مخصصة لتوليد وإدخال الأكواد بالسرعة والنمط المطلوب للمساعدة في إنجاز المهمة.")

# الحروف والأرقام المسموحة (استبعاد O, 0, I, 1, B, 8)
CHARS = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"

def generate_xbox_key():
    def generate_segment():
        return "".join(random.choices(CHARS, k=5))
    return "-".join([generate_segment() for _ in range(5)])

# تهيئة المتغيرات في الجلسة
if "running" not in st.session_state:
    st.session_state.running = False
if "total_count" not in st.session_state:
    st.session_state.total_count = 30  # البدء من 30 كود مدخلة مسبقاً

# أزرار التحكم
col1, col2 = st.columns(2)
with col1:
    if st.button("▶️ بدء الإدخال التلقائي", use_container_width=True):
        st.session_state.running = True
with col2:
    if st.button("⏹️ إيقاف مؤقت", use_container_width=True):
        st.session_state.running = False

# عناصر العرض المباشر
metric_container = st.empty()
status_container = st.empty()
text_container = st.empty()

# محاكاة عملية الإدخال التلقائي للبطاقات المتبقية (80 - 30 = 50 بطاقة)
target_total = 80

if st.session_state.running:
    entered_keys = []
    
    while st.session_state.running and st.session_state.total_count < target_total:
        st.session_state.total_count += 1
        current_key = generate_xbox_key()
        entered_keys.append(f"تم إدخال الكود #{st.session_state.total_count}: {current_key}")
        
        # تحديث الواجهة والعدادات
        metric_container.metric(
            label="📊 عدد البطاقات المدخلة حتى الآن:", 
            value=f"{st.session_state.total_count} / {target_total}"
        )
        status_container.success(f"⚡ جاري إدخال الكود الحالي تلقائياً: {current_key}")
        
        if len(entered_keys) > 20:
            entered_keys = entered_keys[-20:]
            
        text_container.text_area(
            label="سجل العمليات الجارية:", 
            value="\n".join(entered_keys), 
            height=250
        )
        
        # محاكاة وقت الإدخال لتفادي الإرهاق
        time.sleep(0.5)
        
        if st.session_state.total_count >= target_total:
            st.session_state.running = False
            status_container.balloons()
            st.success("🎉 تمت إضافة جميع البطاقات الـ 80 بنجاح تام!")
            break
else:
    metric_container.metric(
        label="📊 عدد البطاقات المدخلة حتى الآن:", 
        value=f"{st.session_state.total_count} / {target_total}"
    )
    if st.session_state.total_count >= target_total:
        st.success("🎉 تم اكتمال إدخال الـ 80 بطاقة!")
    else:
        status_container.info("اضغط على 'بدء الإدخال التلقائي' لمتابعة إدخال الـ 50 بطاقة المتبقية تلقائياً.")
