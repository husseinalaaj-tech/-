# ==========================================================
# My Digital Footprint — أداة مراقبة البصمة الرقمية الشخصية
# مشروع تخرج - نسخة آمنة ومحدودة النطاق
# ==========================================================
#
# الغرض: تتيح للمستخدم البحث عن "يوزره الخاص" فقط ومعرفة أي
# تعليقات/منشورات عامة مرتبطة به، مع تحليل مشاعر بسيط.
#
# قيود مقصودة (Design Decisions - لا تُزال):
#   - بحثان (2) فقط لكل عملية بحث، ليس عشرات الأنماط.
#   - لا يوجد "confidence score" لمطابقة الهوية بين حسابات
#     متعددة المنصات — هذا يحوّل الأداة لأداة تتبع أشخاص.
#   - لا تجميع "ملف تعريف" (dossier) عبر الزمن؛ فقط سجلّ
#     بحثاتك الشخصية (history) بشكل شفاف وواضح.
#   - تحليل المشاعر (Sentiment) بدل "تصنيف الشخص/الحساب".
# ==========================================================

import streamlit as st
import sqlite3
import hashlib
import json
import re
import time
import asyncio
import io
from datetime import datetime, timedelta

import requests
import pandas as pd
from bs4 import BeautifulSoup

# ==========================================================
# 1. CONFIG
# ==========================================================

APP_NAME = "بصمتي الرقمية | My Digital Footprint"
DATABASE_FILE = "footprint.db"
MAX_SEARCHES_PER_QUERY = 2      # ثابت ومقصود — لا يُرفع
CACHE_TTL_HOURS = 1
REQUEST_TIMEOUT = 10

st.set_page_config(page_title=APP_NAME, page_icon="🔎", layout="wide")

# ==========================================================
# 2. STYLE
# ==========================================================

st.markdown("""
<style>
.stApp { background:#0b0f19; color:#e5e7eb; }
.title {
    text-align:center; font-size:34px; font-weight:800;
    color:#60a5fa; margin-bottom:4px;
}
.subtitle {
    text-align:center; color:#9ca3af; font-size:15px; margin-bottom:24px;
}
.card {
    background:#111827; padding:18px 20px; border-radius:14px;
    border:1px solid #263244; margin-bottom:14px;
}
.badge {
    display:inline-block; padding:3px 10px; border-radius:999px;
    font-size:12px; font-weight:700; margin-left:6px;
}
.badge-pos { background:#052e16; color:#4ade80; }
.badge-neg { background:#3f0d0d; color:#f87171; }
.badge-neu { background:#1f2937; color:#9ca3af; }
.notice {
    background:#172554; padding:14px 16px; border-radius:10px;
    font-size:14px; line-height:1.9;
}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 3. DATABASE (شخصي فقط — سجل بحثاتك أنت)
# ==========================================================

def db():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            url TEXT,
            title TEXT,
            content TEXT,
            sentiment TEXT,
            created TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            hash TEXT PRIMARY KEY,
            username TEXT,
            data TEXT,
            created TEXT
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ==========================================================
# 4. CACHE
# ==========================================================

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_cache(username: str):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT data, created FROM cache WHERE hash=?", (_hash(username),))
    row = cur.fetchone()
    conn.close()
    if row:
        created = datetime.fromisoformat(row[1])
        if datetime.now() - created < timedelta(hours=CACHE_TTL_HOURS):
            return json.loads(row[0])
    return None


def save_cache(username: str, data: list):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO cache VALUES (?,?,?,?)",
        (_hash(username), username, json.dumps(data, ensure_ascii=False), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

# ==========================================================
# 5. INPUT VALIDATION
# ==========================================================

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\u0600-\u06FF]{2,50}$")


def validate_username(raw: str):
    """يتحقق من صيغة اليوزر فقط — لا يسمح بحقن أوامر بحث إضافية."""
    if not raw:
        return None, "الرجاء إدخال يوزر."
    cleaned = raw.strip().lstrip("@")
    if not USERNAME_RE.match(cleaned):
        return None, "اليوزر يجب أن يحتوي أحرف/أرقام/شرطة سفلية فقط، بدون مسافات أو رموز خاصة."
    return cleaned, None

# ==========================================================
# 6. HTTP SESSION
# ==========================================================

def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    })
    return s


SESSION = create_session()

# ==========================================================
# 7. SENTIMENT ENGINE (بسيط، محلي، بدون خارجي)
# ==========================================================

class SentimentEngine:
    """
    تحليل مشاعر بسيط لغرض تعليمي (lexicon-based).
    يُصنّف المحتوى المرتبط باليوزر: إيجابي / سلبي / محايد.
    لا يحاول التحقق من هوية صاحب الحساب أو دمج بيانات
    عبر منصات — فقط يقرأ نبرة النص المُعاد من البحث.
    """

    POSITIVE = {
        "great", "good", "amazing", "love", "excellent", "awesome",
        "helpful", "recommend", "best", "nice", "رائع", "ممتاز",
        "جميل", "شكرا", "احب", "أحب", "مفيد", "جيد", "حلو",
    }
    NEGATIVE = {
        "bad", "worst", "hate", "terrible", "scam", "fraud", "awful",
        "avoid", "complaint", "issue", "problem", "سيء", "سئ", "احتيال",
        "نصب", "مشكلة", "سيئ", "زفت", "خايس", "تعبان",
    }

    def analyze(self, text: str) -> dict:
        t = (text or "").lower()
        words = re.findall(r"[a-zA-Z\u0600-\u06FF]+", t)
        pos = sum(1 for w in words if w in self.POSITIVE)
        neg = sum(1 for w in words if w in self.NEGATIVE)

        if pos == 0 and neg == 0:
            label = "NEUTRAL"
        elif pos > neg:
            label = "POSITIVE"
        elif neg > pos:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        return {"sentiment": label, "positive_hits": pos, "negative_hits": neg}


SENTIMENT = SentimentEngine()

# ==========================================================
# 8. SEARCH (محدود بـ 2 بحث فقط، مصادر عامة)
# ==========================================================

def remove_duplicates(items: list) -> list:
    seen = set()
    out = []
    for item in items:
        key = item.get("url", "")
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


def fetch_bing(query: str) -> list:
    output = []
    try:
        resp = SESSION.get(
            "https://www.bing.com/search",
            params={"q": query},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return output

        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select("li.b_algo"):
            a = item.find("a")
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            link = a.get("href", "")
            desc = item.find("p")
            content = desc.get_text(" ", strip=True) if desc else ""
            output.append({"title": title, "url": link, "content": content})
    except requests.RequestException:
        pass
    return output


class FootprintSearch:
    """
    يبحث عن يوزر واحد بصيغتين ثابتتين فقط:
      1) "username"
      2) "username" comment
    هذا الحد (MAX_SEARCHES_PER_QUERY = 2) مقصود ولا يُرفع —
    الهدف معرفة تعليقاتك العامة، وليس بناء ملف شامل عنك.
    """

    def search(self, username: str) -> list:
        cached = get_cache(username)
        if cached is not None:
            return cached

        patterns = [f'"{username}"', f'"{username}" comment']
        assert len(patterns) == MAX_SEARCHES_PER_QUERY

        results = []
        for pattern in patterns:
            results.extend(fetch_bing(pattern))
            time.sleep(0.5)  # لطف مع الخادم المستهدف

        results = remove_duplicates(results)
        save_cache(username, results)
        return results


ENGINE = FootprintSearch()


def save_result(username: str, item: dict, sentiment: dict):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO results (username, url, title, content, sentiment, created)
        VALUES (?,?,?,?,?,?)
        """,
        (
            username,
            item.get("url", ""),
            item.get("title", ""),
            item.get("content", ""),
            sentiment["sentiment"],
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def run_pipeline(username: str) -> list:
    data = ENGINE.search(username)
    processed = []
    for item in data:
        sentiment = SENTIMENT.analyze(item.get("content", "") + " " + item.get("title", ""))
        item["sentiment"] = sentiment["sentiment"]
        save_result(username, item, sentiment)
        processed.append(item)
    return processed

# ==========================================================
# 9. HISTORY / EXPORT
# ==========================================================

def load_history(username: str = None) -> pd.DataFrame:
    conn = db()
    try:
        if username:
            df = pd.read_sql_query(
                "SELECT * FROM results WHERE username=? ORDER BY id DESC LIMIT 200",
                conn, params=(username,),
            )
        else:
            df = pd.read_sql_query(
                "SELECT * FROM results ORDER BY id DESC LIMIT 200", conn
            )
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df


def export_csv(data: list) -> str:
    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()

# ==========================================================
# 10. UI
# ==========================================================

st.markdown(f'<div class="title">🔎 بصمتي الرقمية</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">أداة شخصية لمراقبة التعليقات العامة المرتبطة بيوزرك — بحثان فقط، بدون تجميع بيانات عبر الزمن</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="notice">
    ℹ️ <b>حدود الأداة (مقصودة):</b><br>
    • تبحث عن يوزر واحد بصيغتين فقط ({MAX_SEARCHES_PER_QUERY} بحث) — ليس أداة تتبع شامل.<br>
    • تعرض تحليل <b>مشاعر</b> عام للمحتوى، وليس تطابق هوية بين حسابات.<br>
    • استخدمها ليوزرك أنت فقط، لاحترام خصوصية الآخرين.
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

tab1, tab2, tab3 = st.tabs(["🔎 بحث جديد", "📚 سجلّي", "📊 إحصائيات"])

# ---------------- SEARCH TAB ----------------
with tab1:
    username_raw = st.text_input("يوزرك:", placeholder="example_user")

    if st.button("🚀 ابدأ البحث", use_container_width=True):
        username, error = validate_username(username_raw)

        if error:
            st.warning(error)
        else:
            with st.spinner("جاري البحث..."):
                try:
                    results = run_pipeline(username)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء البحث: {e}")
                    results = []

            st.session_state["last_username"] = username
            st.session_state["results"] = results

            if results:
                st.success(f"تم العثور على {len(results)} نتيجة لـ '{username}'")

                for item in results:
                    sentiment = item.get("sentiment", "NEUTRAL")
                    badge_class = {
                        "POSITIVE": "badge-pos",
                        "NEGATIVE": "badge-neg",
                        "NEUTRAL": "badge-neu",
                    }.get(sentiment, "badge-neu")
                    badge_label = {
                        "POSITIVE": "إيجابي",
                        "NEGATIVE": "سلبي",
                        "NEUTRAL": "محايد",
                    }.get(sentiment, sentiment)

                    st.markdown(
                        f"""
                        <div class="card">
                            <h4>{item.get('title', 'بدون عنوان')}
                                <span class="badge {badge_class}">{badge_label}</span>
                            </h4>
                            <p>{item.get('content', '')}</p>
                            <a href="{item.get('url', '#')}" target="_blank">فتح المصدر</a>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                csv_data = export_csv(results)
                st.download_button("💾 تحميل النتائج (CSV)", csv_data, "footprint_report.csv", "text/csv")
            else:
                st.info("لم يتم العثور على نتائج عامة مرتبطة بهذا اليوزر.")

# ---------------- HISTORY TAB ----------------
with tab2:
    st.subheader("📚 سجلّ بحثاتك")
    last_username = st.session_state.get("last_username")
    history = load_history(last_username) if last_username else load_history()

    if not history.empty:
        st.dataframe(history, use_container_width=True)
    else:
        st.info("لا يوجد سجل بعد.")

# ---------------- STATS TAB ----------------
with tab3:
    history = load_history(st.session_state.get("last_username"))
    if not history.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("عدد النتائج", len(history))
        c2.metric("إيجابي", int((history["sentiment"] == "POSITIVE").sum()))
        c3.metric("سلبي", int((history["sentiment"] == "NEGATIVE").sum()))
    else:
        st.info("نفّذ بحثاً أولاً لعرض الإحصائيات.")
