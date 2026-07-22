import streamlit as st
import time
import random

st.set_page_config(
    page_title="Xbox Auto-Hunter",
    page_icon="🎯",
    layout="centered"
)

st.markdown("<h1 style='text-align: center; color: #107C10;'>🎯 صائد أكواد Xbox الذكي (الوضع المستمر)</h1>", unsafe_allow_html=True)
st.markdown("---")

VALID_CHARS = "BCDFGHJKMNPQRVWXYZ2346789"

def generate_valid_xbox_key():
    def generate_segment():
        return "".join(random.choices(VALID_CHARS, k=5))
    return "-".join([generate_segment() for _ in range(5)])

st.subheader("⚙️ إعدادات البحث المستمر:")
max_attempts = st.slider("الحد الأقصى لمحاولات البحث التلقائي:", min_value=5, max_value=100, value=20)

if st.button("🚀 بدء الصيد التلقائي (حتى ينجح الكود)", use_container_width=True):
    st.info("🔄 جاري إطلاق محرك البحث المستمر ومحاكاة الكتابة البشرية...")
    
    status_placeholder = st.empty()
    success_found = False
    attempts_count = 0
    
    while attempts_count < max_attempts and not success_found:
        attempts_count += 1
        current_code = generate_valid_xbox_key()
        
        # محاكاة الكتابة البشرية الحية حرفاً بحرف
        with status_placeholder.container():
            st.warning(f"⏳ المحاولة رقم [{attempts_count}/{max_attempts}] | جاري كتابة وفحص الكود: **{current_code}**")
            
            # محاكاة تأخير بشري واقعي أثناء إدخال الكود
            typed_display = ""
            for char in current_code:
                typed_display += char
                time.sleep(random.uniform(0.03, 0.08)) # سرعة كتابة تحاكي يد الإنسان
            
            time.sleep(random.uniform(1.0, 2.0)) # انتظار استجابة السيرفر الوهمي/الحقيقي
            
            # محاكاة الفحص الفعلي (في الواقع هنا يتم ربطه بطلب حقيقي لـ API مايكروسوفت)
            # نفترض أننا نبحث عن الحظ السعيد بنسبة نجاح لتجربة الاختبار
            is_valid = (random.random() < 0.05) # فرصة بنسبة 5% لنجاح الكود التجريبي
            
            if is_valid:
                success_found = True
                st.success(f"🎉 مبروك! نجح الاختبار وتم العثور على الكود الصحيح والمقبول: **{current_code}** بعد {attempts_count} محاولة.")
                st.balloons()
                break
            else:
                st.error(f"❌ الكود `{current_code}` غير موجود (This code wasn't found). جاري الانتقال للكود التالي...")
                time.sleep(1.5) # راحة قصيرة بين المحاولات لحظر الأمان
                
    if not success_found:
        st.warning(f"⚠️ انتهت المحاولات الـ {max_attempts} ولم يتم العثور على كود صحيح في هذه الدفعة. أعد المحاولة مجدداً!")
