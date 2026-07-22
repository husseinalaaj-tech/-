import streamlit as st
import random

# إعدادات الصفحة
st.set_page_config(
    page_title="Bulk Random Key Generator",
    page_icon="🔑",
    layout="centered"
)

st.title("🔑 مولّد المفاتيح العشوائية بالجملة")
st.markdown("أداة لتوليد كميات كبيرة من المفاتيح العشوائية بسرعة فائقة بضغطة زر واحدة.")

# القائمة الجانبية للتحكم بالعدد
st.sidebar.header("إعدادات التوليد")
num_keys = st.sidebar.slider("عدد المفاتيح في المرة الواحدة:", min_value=5, max_value=100, value=20, step=5)

def generate_random_key():
    chars = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"
    def generate_segment():
        return "".join(random.choices(chars, k=5))
    return "-".join([generate_segment() for _ in range(5)])

# زر التوليد الجماعي
if st.button(f"⚡ توليد {num_keys} مفتاحاً الآن", use_container_width=True):
    # توليد قائمة المفاتيح بسرعة
    keys_list = [generate_random_key() for _ in range(num_keys)]
    
    st.success(f"تم توليد {num_keys} مفتاحاً بنجاح:")
    
    # دمج المفاتيح في نص واحد مفصول بأسطر لسهولة النسخ
    all_keys_text = "\n".join(keys_list)
    
    # عرضها في صندوق نصي واحد قابل للنسخ بالكامل
    st.text_area("قائمة المفاتيح (انسخ الكل):", value=all_keys_text, height=250)
else:
    st.info("اضغط على الزر أعلاه لتوليد الدفعة الأولى من المفاتيح.")
