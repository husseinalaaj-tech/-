import streamlit as st

st.set_page_config(page_title="Xbox Redeemer", page_icon="🎮")

st.title("🎮 أداة إدارة الأكواد المبسطة")

# قائمة تجريبية للأكواد
codes = ["XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"]

codes_input = st.text_area("الأكواد:", value="\n".join(codes), height=150)

if st.button("بدء المعالجة"):
    st.info("جاري تجهيز الأكواد...")
    processed_codes = [c.strip() for c in codes_input.split("\n") if c.strip()]
    # تم إضافة علامات التنصيص هنا لحل المشكلة
    st.success(f"تم تجهيز {len(processed_codes)} كود بنجاح للمعالجة الآمنة.")
