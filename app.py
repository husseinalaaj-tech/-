# ==========================================================
# Deep Intelligence AI - Password Profiler
# Instagram Account Cracking Assistant
# ==========================================================

import streamlit as st
import re
import time
import random
import pandas as pd
import io

# ==========================================================
# 1. STREAMLIT SETTINGS & UI
# ==========================================================

st.set_page_config(
    page_title="AI Password Profiler",
    page_icon="🗝️",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background:#0b0f19; color:white; }
.title { text-align:center; font-size:40px; font-weight:900; color:#ef4444; }
.card { background:#111827; padding:20px; border-radius:15px; border:1px solid #374151; margin-bottom:15px; }
.warning-box { background:#450a0a; padding:15px; border-radius:10px; border-left: 5px solid #dc2626; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)


# ==========================================================
# 2. AI PASSWORD GENERATION ENGINE
# ==========================================================

class AIPasswordGuesser:
    def __init__(self, target_username, depth=2):
        self.username = str(target_username).lower().strip()
        self.depth = depth # 1: Low, 2: Medium, 3: Deep
        self.generated_passwords = []
        
    def _extract_bases(self):
        """تفكيك اليوزر لاستخراج الأسماء والمقاطع"""
        bases = [self.username]
        # تقسيم اليوزر بناءً على النقاط والأرقام والشرطات
        parts = re.split(r'[^a-zA-Z]', self.username)
        parts = [p for p in parts if len(p) > 2]
        bases.extend(parts)
        
        # استخراج الأرقام الموجودة في اليوزر
        numbers = re.findall(r'\d+', self.username)
        
        return list(set(bases)), numbers

    def _get_common_suffixes(self):
        """قائمة النهايات الشائعة (أرقام، تواريخ ميلاد)"""
        years = [str(y) for y in range(1990, 2011)]
        common_nums = ['123', '1234', '12345', '1122', '0000', '123123', '111']
        return years + common_nums

    def generate(self):
        bases, embedded_numbers = self._extract_bases()
        suffixes = self._get_common_suffixes()
        symbols = ['@', '_', '.', '#']
        
        results = []

        # القاعدة 1: اليوزر نفسه كتخمين أولي
        results.append({"password": self.username, "confidence": 85, "reason": "Exact Username"})
        results.append({"password": self.username + "123", "confidence": 90, "reason": "Username + 123"})
        
        # القاعدة 2: دمج المقاطع مع بعضها ومع الأرقام
        for base in bases:
            capitalized = base.capitalize()
            
            # الأسماء بدون إضافات
            results.append({"password": base, "confidence": 60, "reason": "Base Word"})
            results.append({"password": capitalized, "confidence": 65, "reason": "Capitalized Base"})
            results.append({"password": base + base, "confidence": 70, "reason": "Double Base"})

            # دمج مع النهايات الشائعة وتواريخ الميلاد
            for suff in suffixes:
                results.append({"password": base + suff, "confidence": 80, "reason": "Base + Numbers/Date"})
                results.append({"password": capitalized + suff, "confidence": 85, "reason": "Capitalized + Date"})
                
                if self.depth >= 2:
                    results.append({"password": base + "_" + suff, "confidence": 75, "reason": "Base + _ + Numbers"})
                    results.append({"password": base + "@" + suff, "confidence": 75, "reason": "Base + @ + Numbers"})

        # القاعدة 3: استخدام الأرقام المستخرجة من اليوزر نفسه (قوية جداً)
        for base in bases:
            for num in embedded_numbers:
                if num not in base:
                    results.append({"password": base + num, "confidence": 95, "reason": "Base + Embedded User Number"})
                    
        # القاعدة 4: كلمات مرور عالمية شائعة (إذا كان العمق عالي)
        if self.depth >= 3:
            global_weak = ['qwerty', '123456789', 'password', 'iloveyou']
            for w in global_weak:
                results.append({"password": w, "confidence": 40, "reason": "Global Weak Password"})
                results.append({"password": self.username + w, "confidence": 50, "reason": "User + Weak"})

        # تنظيف التكرار وترتيب حسب نسبة الثقة
        unique_results = {}
        for item in results:
            pwd = item["password"]
            # لا نضيف كلمات المرور القصيرة جداً
            if len(pwd) >= 6:
                if pwd not in unique_results or unique_results[pwd]["confidence"] < item["confidence"]:
                    unique_results[pwd] = item

        final_list = list(unique_results.values())
        final_list.sort(key=lambda x: x["confidence"], reverse=True)
        
        return final_list


# ==========================================================
# 3. EXPORT FUNCTION
# ==========================================================
def export_wordlist(data):
    """تصدير كلمات المرور كملف نصي (Wordlist) لاستخدامه في برامج الاختراق"""
    content = "\n".join([item["password"] for item in data])
    return content


# ==========================================================
# 4. APPLICATION UI
# ==========================================================

st.markdown('<div class="title">🗝️ AI Password Profiler</div>', unsafe_allow_html=True)

st.markdown("""
<div class="warning-box">
<b>⚠️ تنبيه النظام:</b> هذه الأداة تستخدم خوارزميات تحليل السلوك البشري لتوليد قائمة تخمينات (Wordlist) مخصصة لحساب محدد بناءً على بنية اليوزر نيم.
</div>
""", unsafe_allow_html=True)

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("⚙️ إعدادات التخمين")
    
    depth_level = st.select_slider(
        "عمق التحليل (الذكاء الاصطناعي)",
        options=[1, 2, 3],
        value=2,
        format_func=lambda x: "سريع" if x==1 else ("متوسط" if x==2 else "عميق (مكثف)")
    )
    
    max_results = st.number_input("الحد الأقصى للنتائج", min_value=10, max_value=5000, value=100)
    
    st.divider()
    st.write("حالة المحرك: 🟢 متصل")

# ---------------- Main App ----------------

query = st.text_input("👤 أدخل يوزر حساب الإنستغرام:", placeholder="مثال: ahmed_1999 أو frozen.guy")

if st.button("🧠 بدء توليد كلمات المرور", use_container_width=True):
    if not query.strip():
        st.warning("الرجاء إدخال يوزر نيم أولاً!")
    else:
        status = st.empty()
        progress = st.progress(0)
        
        # محاكاة التفكير والتحليل
        status.info("🔍 جاري تحليل بنية اليوزر واستخراج البيانات التكتيكية...")
        time.sleep(1)
        progress.progress(30)
        
        status.info("⚙️ جاري دمج المقاطع مع قواعد البيانات السلوكية...")
        time.sleep(1)
        progress.progress(70)
        
        # تشغيل المحرك
        engine = AIPasswordGuesser(target_username=query, depth=depth_level)
        results = engine.generate()
        
        # تقييد عدد النتائج
        results = results[:max_results]
        
        progress.progress(100)
        status.success(f"✅ اكتمل التحليل! تم توليد {len(results)} كلمة مرور محتملة.")
        
        # عرض النتائج
        st.subheader("📋 قائمة التخمينات الذكية:")
        
        # تجهيز البيانات للعرض في جدول
        df = pd.DataFrame(results)
        df.rename(columns={"password": "كلمة المرور", "confidence": "نسبة الاحتمالية (%)", "reason": "سبب التخمين (AI Logic)"}, inplace=True)
        
        # عرض الجدول بشكل طبيعي بدون التلوين الذي يتطلب matplotlib
        st.dataframe(
            df,
            use_container_width=True,
            height=400
        )
        
        # زر تحميل ملف Wordlist للـ Brute Force
        st.divider()
        wordlist_txt = export_wordlist(results)
        
        st.download_button(
            label="💾 تحميل كملف Wordlist (.txt)",
            data=wordlist_txt,
            file_name=f"{query}_wordlist.txt",
            mime="text/plain",
            use_container_width=True
        )
