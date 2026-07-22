import streamlit as st
import time
import random

st.set_page_config(
    page_title="Xbox Code Validator",
    page_icon="🎮",
    layout="centered"
)

st.markdown("<h1 style='text-align: center; color: #107C10;'>🎮 فاحص أكواد Xbox المتوافق</h1>", unsafe_allow_html=True)
st.markdown("---")

# الحروف والأرقام المسموحة رسمياً (تم استبعاد A, E, I, O, U, L, S, 0, 1, 5)
VALID_CHARS = "BCDFGHJKMNPQRVWXYZ2346789"

def generate_valid_xbox_key():
    def generate_segment():
        return "".join(random.choices(VALID_CHARS, k=5))
    return "-".join([generate_segment() for _ in range(5)])

# صندوق إدخال الأكواد
default_code = generate_valid_xbox_key()
codes_input = st.text_area(
    "أدخل الأكواد (كل كود في سطر):", 
    value=default_code, 
    height=150
)

if st.button("🚀 فحص الأكواد وتتبع الحالة", use_container_width=True):
    raw_codes = [c.strip().upper() for c in codes_input.split("\n") if c.strip()]
    
    if not raw_codes:
        st.warning("⚠️ الرجاء إدخال كود واحد على الأقل.")
    else:
        total_count = len(raw_codes)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="الإجمالي", value=total_count)
        metric_success = col2.empty()
        metric_failed = col3.empty()
        
        metric_success.metric(label="✅ المقبول", value=0)
        metric_failed.metric(label="❌ المرفوض", value=0)
        
        st.markdown("---")
        
        accepted_list = []
        failed_list = []
        
        for i, code in enumerate(raw_codes, 1):
            with st.spinner(f"جاري فحص الكود [{i}/{total_count}]: {code}..."):
                time.sleep(1.0)
                
                # التحقق برمجيياً هل الكود يحتوي على حروف ممنوعة حسب شروط مايكروسوفت
                has_invalid_char = any(char in code for char in "AEIOULSO150")
                
                if has_invalid_char or len(code) != 29: # طول كود إكس بوكس الصحيح مع الفواصل هو 29
                    failed_list.append(code)
                    st.error(f"[{i}/{total_count}] الكود **{code}** ➔ مرفوض (يحتوي على رموز غير مسموحة أو صيغة غير صحيحة)")
                else:
                    accepted_list.append(code)
                    st.success(f"[{i}/{total_count}] الكود **{code}** ➔ متوافق مع شروط الدومين ويمكن إرساله بنجاح")
                
                metric_success.metric(label="✅ المقبول", value=len(accepted_list))
                metric_failed.metric(label="❌ المرفوض", value=len(failed_list))
        
        st.success("🎉 انتهى الفحص بنجاح!")
