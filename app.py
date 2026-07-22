import random
import time
from playwright.sync_api import sync_playwright

def human_type(page, selector, text):
    """محاكاة الكتابة البشرية ببطء وتفاوت عشوائي لتجنب الحظر"""
    page.click(selector)
    for char in text:
        page.type(selector, char, delay=random.randint(80, 250))
        time.sleep(random.uniform(0.05, 0.2))

def strongest_redeem_bot(codes_list):
    with sync_playwright() as p:
        # تشغيل المتصفح بوضع مرئي مع تفعيل إعدادات منع كشف البوتات
        browser = p.chromium.launch(
            headless=False, 
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        # الانتقال لصفحة الدعم الرسمية
        page.goto("https://support.xbox.com/")
        print("[*] تم فتح الصفحة بنجاح، جاري بدء العملية...")
        
        successful = []
        failed = []

        for i, code in enumerate(codes_list, 1):
            try:
                print(f"[*] جاري معالجة الكود [{i}/{len(codes_list)}]: {code}")
                
                # افتراض وجود حقل الإدخال وزر التفعيل (تعديل المحددات حسب الصفحة الرسمية)
                input_selector = "input#redemption-code"
                submit_selector = "button#submit-code"
                
                page.wait_for_selector(input_selector, timeout=10000)
                page.fill(input_selector, "") # تفريغ الحقل
                
                # كتابة الكود بطريقة بشرية
                human_type(page, input_selector, code)
                
                # فاصل قصير قبل الضغط على زر الإرسال
                time.sleep(random.uniform(1.0, 2.5))
                page.click(submit_selector)
                
                # انتظار استجابة النظام
                time.sleep(random.uniform(4.0, 7.0))
                
                successful.append(code)
                print([+] تم إرسال الكود بنجاح: {code})
                
                # فاصل زمني عشوائي كبير نسبياً بين كل كود والذي يليه لتجنب الحظر المؤقت
                sleep_time = random.uniform(12.0, 25.0)
                print(f"[*] انتظار مؤقت لمدة {round(sleep_time, 2)} ثانية لحماية الحساب...")
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"[-] حدث خطأ مع الكود {code}: {str(e)}")
                failed.append(code)
                time.sleep(5)
                
        browser.close()
        print(f"[!] انتهت العملية. النجاح: {len(successful)} | الفشل: {len(failed)}")

# مثال تجريبي لقائمة الأكواد
# sample_codes = ["XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"]
# strongest_redeem_bot(sample_codes)
