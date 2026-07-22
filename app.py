import streamlit as st
import random
import time
import subprocess
import sys

# إعدادات الصفحة
st.set_page_config(
    page_title="Xbox Advanced Auto-Redeemer",
    page_icon="🎮",
    layout="centered"
)

st.title("🎮 أداة الأتمتة المتقدمة لاسترداد بطاقات Xbox")
st.markdown("نسخة متطورة تعمل عبر محاكاة المتصفح الذكي من داخل واجهة Streamlit.")

# الحروف والأرقام المسموحة
CHARS = "ACDEFGHJKLMNOPQRSTUVWXYZ2345679"

def generate_xbox_key():
    def generate_segment():
        return "".join(random.choices(CHARS, k=5))
    return "-".join([generate_segment() for _ in range(5)])

# تهيئة الجلسة
if "codes_list" not in st.session_state:
    st.session_state.codes_list = [generate_xbox_key() for _ in range(5)]

st.subheader("📋 قائمة الأكواد المراد إرسالها:")
codes_input = st.text_area(
    "يمكنك تعديل الأكواد (كل كود في سطر مستقل):", 
    value="\n".join(st.session_state.codes_list),
    height=150
)

# زر البدء والتنفيذ
if st.button("🚀 تشغيل نظام الأتمتة الذكي", use_container_width=True):
    updated_codes = [c.strip() for c in codes_input.split("\n") if c.strip()]
    
    if not updated_codes:
        st.warning("⚠️ الرجاء إدخال كود واحد على الأقل.")
    else:
        st.info("🔄 جاري إطلاق محرك الأتمتة في الخلفية لتنفيذ العملية بأمان...")
        
        # كود بايثون الداخلي الذي سيتم تشغيله في الخلفية لتجنب تجميد واجهة Streamlit
        script_content = f"""
import time
import random
from playwright.sync_api import sync_playwright

codes = {updated_codes}

def human_type(page, selector, text):
    page.click(selector)
    for char in text:
        page.type(selector, char, delay=random.randint(60, 180))
        time.sleep(random.uniform(0.04, 0.15))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()
    page.goto("https://support.xbox.com/")
    time.sleep(3)
    
    for code in codes:
        try:
            input_selector = "input#redemption-code"
            submit_selector = "button#submit-code"
            
            page.wait_for_selector(input_selector, timeout=5000)
            page.fill(input_selector, "")
            human_type(page, input_selector, code)
            time.sleep(random.uniform(1.0, 2.0))
            page.click(submit_selector)
            time.sleep(random.uniform(3.0, 5.0))
        except Exception as e:
            print(f"Error with {{code}}: {{e}}")
            
    browser.close()
"""
        # كتابة الكود في ملف مؤقت وتشغيله كعملية منفصلة
        with open("worker_bot.py", "w", encoding="utf-8") as f:
            f.write(script_content)
            
        # تشغيل العملية في الخلفية
        subprocess.Popen([sys.executable, "worker_bot.py"])
        st.success("✅ تم تشغيل المتصفح الذكي بنجاح في الخلفية! يمكنك مراقبة النافذة التي ستفتح تلقائياً.")
