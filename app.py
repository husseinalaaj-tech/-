# ==========================================================
# 🕵️‍♂️ Instagram OSINT Analyzer
# ==========================================================

import streamlit as st
import instaloader
import requests
from PIL import Image
from io import BytesIO
import pandas as pd

# ==========================================================
# 1. إعدادات الواجهة
# ==========================================================
st.set_page_config(page_title="IG Analyzer", page_icon="🕵️", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: white; }
.metric-box { background: #1f2937; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #374151; }
.bio-box { background: #111827; padding: 15px; border-radius: 10px; border-left: 4px solid #e1306c; font-family: monospace;}
</style>
""", unsafe_allow_html=True)

st.title("🕵️‍♂️ محلل حسابات إنستغرام (OSINT)")
st.write("أدخل يوزر الحساب لاستخراج البيانات العامة (Public Data) المتاحة.")

# ==========================================================
# 2. إعداد محرك الاستخراج
# ==========================================================
@st.cache_resource
def get_loader():
    L = instaloader.Instaloader()
    # إيقاف تحميل الفيديوهات لتسريع العملية
    L.download_videos = False 
    return L

loader = get_loader()

# ==========================================================
# 3. واجهة الإدخال والتحليل
# ==========================================================
col1, col2 = st.columns([3, 1])

with col1:
    target_username = st.text_input("🔍 أدخل اليوزر (بدون @):", placeholder="مثال: cristiano")

with col2:
    st.write("")
    st.write("")
    analyze_btn = st.button("🚀 بدء التحليل", use_container_width=True)

st.divider()

if analyze_btn and target_username:
    target_username = target_username.strip().replace("@", "")
    
    with st.spinner("جاري الاتصال بسيرفرات إنستغرام وجمع البيانات..."):
        try:
            # استخراج ملف الحساب
            profile = instaloader.Profile.from_username(loader.context, target_username)
            
            # --- جلب صورة العرض ---
            try:
                response = requests.get(profile.profile_pic_url)
                img = Image.open(BytesIO(response.content))
            except:
                img = None

            # --- عرض النتائج في الواجهة ---
            
            # القسم العلوي: الصورة والمعلومات الأساسية
            header_col1, header_col2 = st.columns([1, 3])
            
            with header_col1:
                if img:
                    st.image(img, caption=f"@{profile.username}", use_column_width=True)
                else:
                    st.warning("تعذر جلب صورة الحساب")
                    
            with header_col2:
                st.subheader(f"{profile.full_name or 'لا يوجد اسم'} " + ("✅ (موثق)" if profile.is_verified else ""))
                
                # صندوق البايو
                st.markdown('<div class="bio-box">', unsafe_allow_html=True)
                st.write("**السيرة الذاتية (Bio):**")
                st.write(profile.biography if profile.biography else "لا توجد سيرة ذاتية")
                
                if profile.external_url:
                    st.write(f"🔗 **الرابط الخارجي:** [{profile.external_url}]({profile.external_url})")
                st.markdown('</div>', unsafe_allow_html=True)

            st.write("---")
            
            # قسم الإحصائيات (Metrics)
            stat1, stat2, stat3 = st.columns(3)
            stat1.metric(label="👥 المتابعون (Followers)", value=f"{profile.followers:,}")
            stat2.metric(label="👤 يتابع (Following)", value=f"{profile.followees:,}")
            stat3.metric(label="📸 عدد المنشورات (Posts)", value=f"{profile.mediacount:,}")
            
            st.write("---")

            # قسم البيانات التقنية (تفاصيل أعمق)
            st.subheader("⚙️ التحليل التقني للحساب:")
            
            tech_data = {
                "الخاصية": ["حالة الحساب", "حساب تجاري (Business)", "فئة الحساب", "ID الحساب"],
                "النتيجة": [
                    "🔒 برايفت (مغلق)" if profile.is_private else "🌍 عام (Public)",
                    "نعم" if profile.is_business_account else "لا",
                    profile.business_category_name or "غير محدد",
                    profile.userid
                ]
            }
            
            df_tech = pd.DataFrame(tech_data)
            st.table(df_tech)

        except instaloader.exceptions.ProfileNotExistsException:
            st.error("❌ الحساب غير موجود. تأكد من كتابة اليوزر بشكل صحيح.")
        except instaloader.exceptions.ConnectionException:
            st.error("⚠️ تم حظر الطلب مؤقتاً من إنستغرام (Rate Limit). جرب تشغيل VPN أو المحاولة لاحقاً.")
        except Exception as e:
            st.error(f"❌ حدث خطأ غير متوقع: {e}")

