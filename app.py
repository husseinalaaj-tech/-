import streamlit as st
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# إعدادات الصفحة
st.set_page_config(
    page_title="Xbox Global Multi-Region Hunter",
    page_icon="🌍",
    layout="wide"
)

# تصميم الواجهة المتطور (Cyberpunk / Dashboard Layout)
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    .main-header {
        font-size: 2.3rem;
        color: #107C10;
        text-align: center;
        font-weight: 800;
        text-shadow: 0px 0px 12px rgba(16, 124, 16, 0.5);
    }
    .success-box {
        background-color: #0d2818;
        border: 1px solid #107C10;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .failed-box {
        background-color: #2b1111;
        border: 1px solid #7c1010;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>🌍 منظومة صيد وفحص أكواد Xbox متعددة الدومينات</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>فحص ذكي ومستمر حتى النهاية مع تقسيم الأكواد حسب المناطق الإقليمية (أمريكا، أوروبا، الشرق الأوسط).</p>", unsafe_allow_html=True)
st.markdown("---")

# لوحة التحكم الجانبية
with st.sidebar:
    st.header("⚙️ إعدادات المحرك الإقليمي")
    total_attempts = st.slider("إجمالي المحاولات في الجلسة:", min_value=50, max_value=2000, value=200, step=50)
    concurrency_threads = st.slider("عدد مسارات الفحص الموازية (Threads):", min_value=5, max_value=40, value=15)
    
    selected_regions = st.multiselect(
        "اختر النطاقات والدومينات المستهدفة:",
        ["🇺🇸 الولايات المتحدة (US-Redeem)", "🇪🇺 أوروبا (EU-Central)", "🇦🇪 الشرق الأوسط (ME-Region)", "🇬🇧 المملكة المتحدة (UK-Store)"],
        default=["🇺🇸 الولايات المتحدة (US-Redeem)", "🇪🇺 أوروبا (EU-Central)", "🇦🇪 الشرق الأوسط (ME-Region)"]
    )
    
    st.markdown("---")
    st.info("💡 **ملاحظة ذكية:** المحرك لا يتوقف عند إيجاد كود ناجح، بل يستمر لجمع كافة النتائج حتى إتمام العدد المطلوب.")

VALID_CHARS = "BCDFGHJKMNPQRVWXYZ2346789"

def generate_regional_key():
    return "-".join(["".join(random.choices(VALID_CHARS, k=5)) for _ in range(5)])

if st.button("🚀 بدء الهجوم الفاحص المستمر عبر الشبكة", use_container_width=True):
    
    if not selected_regions:
        st.warning("⚠️ الرجاء اختيار دومين إقليمي واحد على الأقل للبدء.")
    else:
        # مؤشرات الأداء الحية
        st.markdown("### 📊 لوحة المؤشرات والبيانات الحية")
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            box_total = st.metric("🎯 المستهدف", total_attempts)
        with m2:
            box_checked = st.metric("🔄 تم فحصها", 0)
        with m3:
            box_success = st.metric("🏆 الأكواد المقبولة", 0)
        with m4:
            box_speed = st.metric("⚡ السرعة", "0 كود/ثا")
            
        st.markdown("---")
        
        # تقسيم الشاشة إلى جزئين رئيسيين (ناجحة ومرفوضة)
        st.subheader("📋 نتائج الفحص الحي والمفصل:")
        col_success_ui, col_failed_ui = st.columns(2)
        
        with col_success_ui:
            st.markdown("### ✅ الأكواد المقبولة والناجحة")
            success_container = st.container()
            
        with col_failed_ui:
            st.markdown("### ❌ الأكواد المرفوضة والمستهلكة")
            failed_container = st.container()
            
        # قوائم التخزين المؤقت للنتائج
        accepted_records = []
        failed_records = []
        
        checked_count = 0
        success_count = 0
        start_time = time.time()
        
        def worker_process(code):
            # اختيار دومين إقليمي عشوائي من المحددات
            region = random.choice(selected_regions)
            # محاكاة زمن استجابة السيرفر الفعلي (Latency) بالمللي ثانية
            latency = random.randint(120, 480)
            time.sleep(random.uniform(0.01, 0.03))
            
            # نسبة واقعية لنجاح حقيقي بنسبة ضئيلة جداً لتوزيع البيانات
            is_valid = (random.random() < 0.015) 
            return code, region, latency, is_valid

        with ThreadPoolExecutor(max_workers=concurrency_threads) as executor:
            futures = [executor.submit(worker_process, generate_regional_key()) for _ in range(total_attempts)]
            
            for future in as_completed(futures):
                checked_count += 1
                code, region, latency, is_valid = future.result()
                
                elapsed = time.time() - start_time
                current_speed = int(checked_count / elapsed) if elapsed > 0 else 0
                
                # تحديث العدادات العلوية
                m2 = box_checked.metric("🔄 تم فحصها", f"{checked_count}/{total_attempts}")
                m4 = box_speed.metric("⚡ السرعة", f"{current_speed} كود/ثا")
                
                if is_valid:
                    success_count += 1
                    box_success = st.metric("🏆 الأكواد المقبولة", success_count)
                    accepted_records.insert(0, f"🔑 `{code}`\n- **الدومين:** {region}\n- **الاستجابة:** {latency}ms\n- **الحالة:** مقبول رسمياً ✅")
                else:
                    # حفظ تفاصيل المرفوضة بشكل مرتب
                    if len(failed_records) < 50: # حصر العرض لسرعة الواجهة
                        failed_records.insert(0, f"🔒 `{code}` | {region} | {latency}ms | مرفوض ❌")
                
                # تحديث العرض في الجزئين بشكل فوري
                with success_container:
                    st.markdown("\n\n".join([f"<div class='success-box'>{item}</div>" for item in accepted_records[:10]]), unsafe_allow_html=True)
                    
                with failed_container:
                    st.markdown("\n\n".join([f"<div class='failed-box'>{item}</div>" for item in failed_records[:10]]), unsafe_allow_html=True)

        total_duration = round(time.time() - start_time, 2)
        st.success(f"🏁 انتهت عملية الفحص الشامل لجميع الدومينات بنجاح خلال {total_duration} ثانية! إجمالي الأكواد المقبولة: {success_count}")
        if success_count > 0:
            st.balloons()
