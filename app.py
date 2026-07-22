# ==========================================================
# Deep Intelligence Analyzer V3
# Graduation Project Edition - Full Integrated Version
# ==========================================================

import streamlit as st
import sqlite3
import json
import hashlib
import time
import re
import os
import asyncio
import requests
import urllib.parse
import pandas as pd
import io
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================================
# 1. PROJECT CONFIGURATION
# ==========================================================

APP_NAME = "Deep Intelligence Analyzer V3"
DATABASE_FILE = "intelligence_cache.db"

# ==========================================================
# 2. STREAMLIT CONFIG
# ==========================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧠",
    layout="wide"
)

# ==========================================================
# 3. GLOBAL STYLE
# ==========================================================

st.markdown("""
<style>
.stApp {
    background:#0b0f19;
    color:white;
}
.title {
    text-align:center;
    font-size:38px;
    font-weight:900;
    color:#3b82f6;
}
.card {
    background:#111827;
    padding:18px;
    border-radius:12px;
    border:1px solid #263244;
    margin-bottom:15px;
}
.metric-box {
    background:#111827;
    padding:15px;
    border-radius:10px;
    text-align:center;
}
</style>
""", unsafe_allow_html=True)


# ==========================================================
# 4. DATABASE SYSTEM
# ==========================================================

def get_db():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)

def init_database():
    conn = get_db()
    cursor = conn.cursor()

    # النتائج
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results
    (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        source TEXT,
        content TEXT,
        confidence INTEGER,
        category TEXT,
        analysis TEXT,
        created_at TEXT
    )
    """)

    # الكاش
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cache
    (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hash TEXT UNIQUE,
        query TEXT,
        response TEXT,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_database()

# ==========================================================
# 5. CACHE SYSTEM
# ==========================================================

def create_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_cache(query):
    h = create_hash(query)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT response FROM cache WHERE hash=?", (h,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return None

def save_cache(query, response):
    h = create_hash(query)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO cache (hash, query, response, created_at)
        VALUES (?,?,?,?)
        """,
        (h, query, json.dumps(response, ensure_ascii=False), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ==========================================================
# 6. SECURITY CLEANER
# ==========================================================

def clean_text(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"[^\w\s@.-]", "", text)
    return text.strip()

# ==========================================================
# 7. ADVANCED AI ENGINE
# ==========================================================

class IntelligenceAI:
    def __init__(self):
        self.version = "AI-V3"

    def keyword_score(self, content):
        keywords = {
            "comment": 10, "profile": 10, "account": 10,
            "user": 5, "post": 5, "instagram": 15, "message": 10
        }
        score = 0
        reasons = []
        lower = content.lower()

        for word, value in keywords.items():
            if word in lower:
                score += value
                reasons.append(f"وجد مؤشر {word}")
        return score, reasons

    def analyze(self, query, content):
        query = query.lower()
        content = content.lower()
        score = 0
        reasons = []

        if query in content:
            score += 40
            reasons.append("تطابق نصي مباشر")

        k_score, k_reason = self.keyword_score(content)
        score += k_score
        reasons.extend(k_reason)

        length = len(content)
        if length > 300:
            score += 15
            reasons.append("محتوى غني")
        elif length > 100:
            score += 8
            reasons.append("محتوى متوسط")

        if score > 100:
            score = 100

        if score >= 70:
            category = "HIGH_MATCH"
        elif score >= 40:
            category = "MEDIUM_MATCH"
        else:
            category = "LOW_MATCH"

        return {
            "confidence": score,
            "category": category,
            "analysis": reasons
        }

AI_ENGINE = IntelligenceAI()

# ==========================================================
# 8. SAVE RESULT
# ==========================================================

def save_result(query, source, content, ai):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO results (query, source, content, confidence, category, analysis, created_at)
        VALUES(?,?,?,?,?,?,?)
        """,
        (query, source, content, ai["confidence"], ai["category"], 
         json.dumps(ai["analysis"], ensure_ascii=False), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

# ==========================================================
# 9. SOURCE RATING SYSTEM
# ==========================================================

def calculate_source_score(url):
    score = 0
    url = url.lower()
    trusted_sources = ["instagram.com", "facebook.com", "youtube.com", "twitter.com", "x.com"]
    medium_sources = ["reddit.com", "github.com", "medium.com"]

    for site in trusted_sources:
        if site in url: score += 30
    for site in medium_sources:
        if site in url: score += 15
    if url.startswith("https"):
        score += 10

    return min(score, 100)

# ==========================================================
# 10. DUPLICATE FILTER
# ==========================================================

def normalize_text(text):
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def remove_duplicates(results):
    unique = []
    seen = set()
    for item in results:
        key = normalize_text(item.get("content", ""))
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique

# ==========================================================
# 11. ONLINE SEARCH ENGINE (WITH STRICT REGEX FILTER)
# ==========================================================

class OnlineSearchEngine:
    def __init__(self, pages=3, workers=5):
        self.pages = pages
        self.workers = workers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    async def search(self, query):
        cached = get_cache(query)
        if cached:
            return cached

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._deep_search, query)
        save_cache(query, result)
        return result

    def _deep_search(self, query):
        safe_query = clean_text(query)
        if not safe_query:
            return []

        search_patterns = [
            f'"{safe_query}"',
            f'"{safe_query}" comments',
            f'"{safe_query}" profile',
            f'site:instagram.com "{safe_query}"'
        ]

        results = []

        def fetch(search_query, page):
            output = []
            try:
                start = (page - 1) * 10 + 1
                url = "https://search.yahoo.com/search?" + urllib.parse.urlencode({"p": search_query, "b": start})
                response = self.session.get(url, timeout=10)
                
                if response.status_code != 200:
                    return []

                soup = BeautifulSoup(response.text, "html.parser")
                for block in soup.find_all("div", class_="compTitle"):
                    link = block.find("a")
                    if not link: continue
                    
                    title = link.text.strip()
                    href = link.get("href", "")
                    text_block = block.find_next_sibling()
                    content = text_block.text.strip() if text_block else ""

                    output.append({
                        "source": href,
                        "title": title,
                        "content": content,
                        "source_score": calculate_source_score(href)
                    })
            except Exception:
                pass
            return output

        jobs = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            for pattern in search_patterns:
                for page in range(1, self.pages + 1):
                    jobs.append(executor.submit(fetch, pattern, page))

            for job in as_completed(jobs):
                results.extend(job.result())

        # حذف التكرار
        results = remove_duplicates(results)

        # 🎯 الفلترة الصارمة (Strict Exact Match Regex): الاستبعاد الكامل لأي نتيجة لا تتطابق حرفياً
        strict_results = []
        regex_pattern = re.compile(rf'(?:^|[^a-zA-Z0-9_.])({re.escape(safe_query)})(?:[^a-zA-Z0-9_.]|$)', re.IGNORECASE)
        
        for item in results:
            text_to_search = f"{item['title']} {item['content']} {urllib.parse.unquote(item['source'])}"
            if regex_pattern.search(text_to_search):
                strict_results.append(item)

        # ترتيب النتائج الصارمة حسب جودة المصدر
        strict_results.sort(key=lambda x: x.get("source_score", 0), reverse=True)

        return strict_results

# ==========================================================
# 12. INTELLIGENCE PIPELINE
# ==========================================================

class IntelligencePipeline:
    def __init__(self, search_engine, ai_engine):
        self.search_engine = search_engine
        self.ai_engine = ai_engine

    async def process(self, query):
        results = await self.search_engine.search(query)
        final = []

        for item in results:
            ai = self.ai_engine.analyze(query, item.get("content", ""))
            data = {
                "source": item.get("source", ""),
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "source_score": item.get("source_score", 0),
                "confidence": ai["confidence"],
                "category": ai["category"],
                "analysis": ai["analysis"]
            }
            save_result(query, data["source"], data["content"], ai)
            final.append(data)

        final.sort(key=lambda x: x["confidence"], reverse=True)
        return final

SEARCH_ENGINE = OnlineSearchEngine(pages=3, workers=5)
PIPELINE = IntelligencePipeline(SEARCH_ENGINE, AI_ENGINE)

# ==========================================================
# 13. DATA HANDLING
# ==========================================================

def load_history():
    conn = get_db()
    try:
        df = pd.read_sql_query("SELECT * FROM results ORDER BY id DESC LIMIT 100", conn)
    except:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

def export_csv(data):
    df = pd.DataFrame(data)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    return buffer.getvalue()

# ==========================================================
# 14. STREAMLIT APPLICATION (UI)
# ==========================================================

st.markdown('<h1 class="title">🧠 Deep Intelligence Analyzer V3</h1>', unsafe_allow_html=True)
st.write("نظام تحليل ذكي متعدد الطبقات مع بحث، تقييم مصادر، وذكاء اصطناعي (مفعل بخاصية التطابق الصارم).")

with st.sidebar:
    st.header("⚙️ التحكم")
    pages = st.slider("عمق البحث (صفحات Yahoo)", 1, 10, 3)
    SEARCH_ENGINE.pages = pages
    st.divider()
    st.info("النظام يحتوي على:\n✓ Cache\n✓ AI Analysis\n✓ Source Ranking\n✓ Strict Regex Filter\n✓ Database History")

tab1, tab2, tab3 = st.tabs(["🔎 تحليل جديد", "📚 السجل", "📊 الإحصائيات"])

# --- تبويب البحث الجديد ---
with tab1:
    query = st.text_input("أدخل يوزر الحساب المستهدف (تطابق تام):", placeholder="مثال: cristiano")
    
    if st.button("🚀 بدء الصيد (الاستخراج العميق)", use_container_width=True):
        if not query.strip():
            st.warning("يرجى إدخال يوزر للبحث.")
        else:
            with st.spinner("جاري الغوص في المحركات وتطبيق الفلترة الصارمة..."):
                results = asyncio.run(PIPELINE.process(query))
            
            st.session_state["last_results"] = results
            
            if len(results) > 0:
                st.success(f"🎯 تم العثور على {len(results)} نتيجة مؤكدة تحتوي على اليوزر '{query}' نصاً وحرفياً.")
                for item in results:
                    # تمييز اليوزر في الواجهة
                    highlighted_content = re.sub(
                        rf'(?:^|[^a-zA-Z0-9_.])({re.escape(query)})(?:[^a-zA-Z0-9_.]|$)',
                        r' <span style="background-color:#ff3d00;color:white;padding:0 3px;border-radius:3px;">\1</span> ',
                        item['content'], flags=re.IGNORECASE
                    )
                    
                    st.markdown(f"""
                    <div class="card">
                        <h4 style="color: #4CAF50;">{item['title']}</h4>
                        <p style="font-size: 14px; line-height: 1.6;">{highlighted_content}</p>
                        <a href="{item['source']}" target="_blank" style="color: #64B5F6;">🔗 رابط المصدر</a>
                        <hr style="border-color:#333; margin:10px 0;">
                        <small>ثقة الذكاء: <b>{item['confidence']}%</b> | تقييم المصدر: <b>{item['source_score']}</b> | التصنيف: <b>{item['category']}</b></small>
                    </div>
                    """, unsafe_allow_html=True)
                
                csv = export_csv(results)
                st.download_button("💾 تحميل التقرير CSV", csv, f"hunt_report_{query}.csv", "text/csv")
            else:
                st.error(f"لم يتم العثور على أي نتائج تتطابق حرفياً مع اليوزر '{query}'. محركات البحث لم تؤرشفه أو تم استبعاده بواسطة الفلتر الصارم لعدم التطابق المستقل.")

# --- تبويب السجل ---
with tab2:
    st.subheader("📚 آخر العمليات")
    history = load_history()
    if not history.empty:
        st.dataframe(history, use_container_width=True)
    else:
        st.info("لا توجد بيانات مسجلة بعد.")

# --- تبويب الإحصائيات ---
with tab3:
    history = load_history()
    if not history.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("عدد التحليلات", len(history))
        c2.metric("متوسط الثقة", f"{round(history['confidence'].mean(), 1)}%")
        c3.metric("المصادر المختلفة", history["source"].nunique())
    else:
        st.info("قم بإجراء بعض العمليات أولاً لظهور الإحصائيات.")
