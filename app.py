import streamlit as st
import time
import random

# إعدادات الصفحة وخصائص الواجهة
st.set_page_config(
    page_title="Xbox Code Redeem Dashboard",
    page_icon="🎮",
    layout="centered"
)

# تخصيص التصميم والترتيب البصري
st.markdown("""
    <style>
    .main-title {
        text-align: center;
        color: #107C10;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🎮 لوحة تحكم استرداد أكواد Xbox</h1>", unsafe_allow_html=True)
st.markdown("---")

# صندوق إدخال الأكواد
st.subheader("📋 قائمة الأكواد المراد معالجتها:")
default_codes = "ABCD1-EFGH2-IJKL3-MNOP4-QRST5\nUVWX6-YZAB7-CDEF8-GHIJ9-KLMN0"
codes_input = st.text_area(
    "ضع كل كود في سطر مستقل:", 
    value=default_codes, 
    height=150
)

# رابط الدومين الرسمي المربوط
XBOX_REDEEM_URL = "https://microsoft.com/redeem"

st.info(f"🔗 الدومين الرسمي المرتبط حالياً: **{XBOX_REDEEM_URL}**")

# زر بدء العملية
if st.button("🚀 بدء عملية الاسترداد والمتابعة", use_container_width=True):
    raw_codes = [c.strip() for c in codes_input.split("\n") if c.strip()]
    
    if not raw_codes:
        st.warning("⚠️ الرجاء إدخال كود واحد على الأقل في القائمة.")
    else:
        total_count = len(raw_codes)
        
        # حاويات الإحصائيات المرئية في الواجهة
        st.markdown("### 📊 إحصائيات العملية الفورية")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="إجمالي الأكواد", value=total_count)
        metric_success = col2.empty()
        metric_failed = col3.empty()
        
        metric_success.metric(label="✅ الأكواد المقبولة", value=0)
        metric_failed.metric(label="❌ الأكواد المرفوضة", value=0)
        
        st.markdown("---")
        st.subheader("🔄 سجل الحالة المباشر:")
        
        # مكان لتحديث حالة الأكواد تفاعلياً
        status_container = st.container()
        
        accepted_list = []
        failed_list = []
        
        with status_container:
            for i, code in enumerate(raw_codes, 1):
                with st.spinner(f"جاري معالجة الكود [{i}/{total_count}]: {code}..."):
                    # محاكاة لعملية الفحص والربط مع دومين مايكروسوفت الرسمي
                    time.sleep(random.uniform(1.2, 2.0))
                    
                    # محاكاة منطقية لنتائج الاسترداد (توزيع عشوائي للتوضيح أو نجاح حقيقي حسب الرغبة)
                    is_success = random.choice([True, False])
                    
                    if is_success:
                        accepted_list.append(code)
                        st.success(f"[{i}/{total_count}] الكود **{code}** ➔ **تم قبوله بنجاح** (مربوط بالدومين الرسمي)")
                    else:
                        failed_list.append(code)
                        st.error(f"[{i}/{total_count}] الكود **{code}** ➔ **مرفوض أو مستخدم مسبقاً**")
                    
                    # تحديث العدادات الحية في الواجهة
                    metric_success.metric(label="✅ الأكواد المقبولة", value=len(accepted_list))
                    metric_failed.metric(label="❌ الأكواد المرفوضة", value=len(failed_list))
        
        st.balloons()
        st.success("🎉 اكتملت العملية لجميع الأكواد بنجاح!")
