# ==========================================================
# Deep Intelligence Analyzer V4
# Graduation Project Edition
# Part 1 / 3
# ==========================================================

import streamlit as st
import sqlite3
import json
import hashlib
import time
import re
import asyncio
import requests
import urllib.parse
import pandas as pd
import io
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==========================================================
# 1. CONFIGURATION
# ==========================================================

APP_NAME = "Deep Intelligence Analyzer V4"
DATABASE_FILE = "deep_intelligence.db"


# ==========================================================
# 2. STREAMLIT SETTINGS
# ==========================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧠",
    layout="wide"
)


# ==========================================================
# 3. UI STYLE
# ==========================================================

st.markdown("""
<style>

.stApp {
    background:#0b0f19;
    color:white;
}

.title {
    text-align:center;
    font-size:40px;
    font-weight:900;
    color:#3b82f6;
}

.card {
    background:#111827;
    padding:20px;
    border-radius:15px;
    border:1px solid #263244;
    margin-bottom:15px;
}

.success-box {
    background:#052e16;
    padding:15px;
    border-radius:10px;
}

.info-box {
    background:#172554;
    padding:15px;
    border-radius:10px;
}

</style>
""", unsafe_allow_html=True)



# ==========================================================
# 4. DATABASE
# ==========================================================

def db():

    return sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )



def init_database():

    conn = db()
    cur = conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS results
    (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        url TEXT,
        title TEXT,
        content TEXT,
        confidence INTEGER,
        ai_reason TEXT,
        created TEXT
    )
    """)



    cur.execute("""
    CREATE TABLE IF NOT EXISTS cache
    (
        hash TEXT PRIMARY KEY,
        query TEXT,
        data TEXT,
        created TEXT
    )
    """)



    conn.commit()
    conn.close()



init_database()



# ==========================================================
# 5. CACHE SYSTEM
# ==========================================================

def hash_text(text):

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()



def get_cache(query):

    conn=db()
    cur=conn.cursor()


    cur.execute(
        """
        SELECT data,created 
        FROM cache
        WHERE hash=?
        """,
        (hash_text(query),)
    )


    row=cur.fetchone()

    conn.close()


    if row:

        created=datetime.fromisoformat(row[1])


        # الكاش صالح ساعة فقط
        if datetime.now()-created < timedelta(hours=1):

            return json.loads(row[0])


    return None




def save_cache(query,data):

    conn=db()
    cur=conn.cursor()


    cur.execute(
        """
        INSERT OR REPLACE INTO cache
        VALUES(?,?,?,?)
        """,
        (
            hash_text(query),
            query,
            json.dumps(data,ensure_ascii=False),
            datetime.now().isoformat()
        )
    )


    conn.commit()
    conn.close()



# ==========================================================
# 6. TEXT CLEANING
# ==========================================================

def clean_text(text):

    if not text:
        return ""

    text=str(text)

    text=re.sub(
        r"[^\w\s@._-]",
        "",
        text
    )

    return text.strip()



# ==========================================================
# 7. LOCAL AI ENGINE
# ==========================================================

class IntelligenceAI:


    def analyze(self,query,text):

        score=0
        reasons=[]


        q=query.lower()
        t=text.lower()


        if q in t:

            score+=50
            reasons.append(
                "تطابق مباشر مع البحث"
            )



        keywords={

            "instagram":15,
            "profile":10,
            "account":10,
            "user":5,
            "comment":10,
            "post":5,
            "message":5

        }



        for word,value in keywords.items():

            if word in t:

                score+=value

                reasons.append(
                    f"مؤشر {word}"
                )



        if len(text)>300:

            score+=10
            reasons.append(
                "محتوى طويل"
            )


        if score>100:
            score=100



        if score>=70:

            category="HIGH"

        elif score>=40:

            category="MEDIUM"

        else:

            category="LOW"



        return {

            "confidence":score,
            "category":category,
            "reasons":reasons

        }



AI=IntelligenceAI()



# ==========================================================
# 8. SAVE RESULTS
# ==========================================================

def save_result(query,item,ai):

    conn=db()
    cur=conn.cursor()


    cur.execute(
    """
    INSERT INTO results
    (
    query,url,title,content,
    confidence,ai_reason,created
    )
    VALUES(?,?,?,?,?,?,?)
    """,
    (
        query,
        item.get("url",""),
        item.get("title",""),
        item.get("content",""),
        ai["confidence"],
        json.dumps(
            ai["reasons"],
            ensure_ascii=False
        ),
        datetime.now().isoformat()
    )
    )


    conn.commit()
    conn.close()



# ==========================================================
# END PART 1
# ========================================================== # ==========================================================
# Deep Intelligence Analyzer V4
# Part 2 / 3
# Search Engine + Filtering + Pipeline
# ==========================================================


# ==========================================================
# 9. HTTP SESSION
# ==========================================================

def create_session():

    session = requests.Session()

    session.headers.update({

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36",

        "Accept-Language":
        "en-US,en;q=0.9"

    })

    return session




# ==========================================================
# 10. SOURCE SCORE
# ==========================================================

def source_score(url):

    score=0

    url=url.lower()


    trusted=[

        "instagram.com",
        "facebook.com",
        "youtube.com",
        "x.com",
        "twitter.com"

    ]


    for site in trusted:

        if site in url:

            score+=30



    if url.startswith("https"):

        score+=10



    return min(score,100)




# ==========================================================
# 11. DUPLICATE REMOVER
# ==========================================================

def remove_duplicates(data):

    result=[]
    seen=set()


    for item in data:

        key=item.get("url","")


        if key not in seen:

            seen.add(key)
            result.append(item)



    return result





# ==========================================================
# 12. REAL SEARCH ENGINE
# ==========================================================

class SearchEngineV4:


    def __init__(self,pages=3):

        self.pages=pages
        self.session=create_session()



    async def search(self,query):


        cached=get_cache(query)


        if cached is not None:

            return cached



        loop=asyncio.get_event_loop()


        results=await loop.run_in_executor(

            None,

            self.deep_search,

            query

        )


        save_cache(query,results)


        return results





    def deep_search(self,query):


        query=clean_text(query)


        if not query:

            return []



        patterns=[

            f'"{query}"',

            f'"{query}" profile',

            f'"{query}" comments',

            f'"{query}" social media'

        ]



        results=[]



        def fetch(search_text,page):

            output=[]


            try:


                start=(page-1)*10


                url="https://www.bing.com/search"


                params={

                    "q":search_text,

                    "first":start

                }



                response=self.session.get(

                    url,

                    params=params,

                    timeout=10

                )



                if response.status_code!=200:

                    return []



                soup=BeautifulSoup(

                    response.text,

                    "html.parser"

                )



                for item in soup.select("li.b_algo"):


                    a=item.find("a")


                    if not a:

                        continue



                    title=a.get_text(
                        " ",
                        strip=True
                    )


                    link=a.get(
                        "href",
                        ""
                    )


                    desc=item.find(
                        "p"
                    )


                    content=""


                    if desc:

                        content=desc.get_text(
                            " ",
                            strip=True
                        )



                    output.append({

                        "title":title,

                        "url":link,

                        "content":content,

                        "source_score":
                        source_score(link)

                    })


            except Exception:

                pass



            return output





        jobs=[]


        with ThreadPoolExecutor(
            max_workers=5
        ) as executor:


            for pattern in patterns:


                for page in range(
                    1,
                    self.pages+1
                ):


                    jobs.append(

                        executor.submit(
                            fetch,
                            pattern,
                            page
                        )

                    )



            for job in as_completed(jobs):

                results.extend(
                    job.result()
                )




        results=remove_duplicates(results)



        # فلترة ذكية
        final=[]


        regex=re.compile(

            rf"(^|[^a-zA-Z0-9_.])"
            rf"{re.escape(query)}"
            rf"([^a-zA-Z0-9_.]|$)",

            re.IGNORECASE

        )



        for item in results:


            text=(

                item["title"]

                +" "

                +item["content"]

                +" "

                +item["url"]

            )



            # لا نحذف كل شيء
            # فقط نرفع النتائج المطابقة للأعلى

            if regex.search(text):

                item["match"]=True

                final.append(item)



            else:

                item["match"]=False

                final.append(item)



        final.sort(

            key=lambda x:(

                x["match"],

                x["source_score"]

            ),

            reverse=True

        )


        return final





# ==========================================================
# 13. PIPELINE
# ==========================================================


class Pipeline:


    def __init__(self):

        self.engine=SearchEngineV4()



    async def run(self,query):


        data=await self.engine.search(query)


        processed=[]


        for item in data:


            ai=AI.analyze(

                query,

                item.get(
                    "content",
                    ""
                )

            )



            item["confidence"]=ai["confidence"]

            item["category"]=ai["category"]

            item["analysis"]=ai["reasons"]



            save_result(
                query,
                item,
                ai
            )



            processed.append(item)



        processed.sort(

            key=lambda x:x["confidence"],

            reverse=True

        )


        return processed





PIPELINE=Pipeline()



# ==========================================================
# END PART 2
# ========================================================== # ==========================================================
# Deep Intelligence Analyzer V4
# Part 3 / 3
# Streamlit Interface
# ==========================================================


# ==========================================================
# 14. HISTORY
# ==========================================================

def load_history():

    conn=db()

    try:

        df=pd.read_sql_query(

            """
            SELECT *
            FROM results
            ORDER BY id DESC
            LIMIT 100
            """,

            conn

        )

    except:

        df=pd.DataFrame()


    conn.close()

    return df





# ==========================================================
# 15. EXPORT
# ==========================================================

def export_csv(data):

    df=pd.DataFrame(data)

    buffer=io.StringIO()

    df.to_csv(

        buffer,

        index=False,

        encoding="utf-8-sig"

    )

    return buffer.getvalue()





# ==========================================================
# 16. APPLICATION UI
# ==========================================================


st.markdown(
    '<div class="title">🧠 Deep Intelligence Analyzer V4</div>',
    unsafe_allow_html=True
)


st.markdown(
"""
<div class="info-box">

نظام تحليل ذكي يحتوي على:

✓ بحث حقيقي بدون API  
✓ محرك بحث متعدد الصفحات  
✓ ذكاء اصطناعي محلي  
✓ تقييم المصادر  
✓ قاعدة بيانات  
✓ نظام Cache  
✓ تقرير CSV  

</div>
""",
unsafe_allow_html=True
)



# ---------------- Sidebar ----------------


with st.sidebar:


    st.header("⚙️ الإعدادات")


    depth=st.slider(

        "عمق البحث",

        1,

        10,

        3

    )


    PIPELINE.engine.pages=depth



    st.divider()


    st.write(
    """
    حالة النظام:

    🟢 محرك البحث فعال

    🟢 AI فعال

    🟢 Database فعال

    """
    )





# ---------------- Tabs ----------------


tab1,tab2,tab3=st.tabs(

    [
        "🔎 بحث جديد",
        "📚 السجل",
        "📊 الإحصائيات"
    ]

)





# ==========================================================
# SEARCH TAB
# ==========================================================


with tab1:


    query=st.text_input(

        "اكتب الكلمة أو اليوزر:",

        placeholder="example_user"

    )



    if st.button(

        "🚀 بدء البحث",

        use_container_width=True

    ):


        if not query.strip():

            st.warning(
                "اكتب كلمة للبحث"
            )


        else:


            status=st.empty()


            progress=st.progress(0)



            try:


                status.info(
                    "🔍 الاتصال بمحرك البحث..."
                )

                progress.progress(
                    20
                )


                results=asyncio.run(

                    PIPELINE.run(
                        query
                    )

                )


                progress.progress(
                    100
                )


                status.success(
                    "اكتمل البحث"
                )



                st.session_state["results"]=results



                if results:


                    st.success(

                        f"تم العثور على {len(results)} نتيجة"

                    )


                    for item in results:



                        match="✅" if item.get(
                            "match"
                        ) else "⚪"



                        st.markdown(
                        f"""
                        <div class="card">

                        <h3>
                        {match}
                        {item.get('title')}
                        </h3>


                        <p>
                        {item.get('content')}
                        </p>


                        <p>
                        🧠 الثقة:
                        {item.get('confidence')}%

                        <br>

                        🌐 تقييم المصدر:
                        {item.get('source_score')}

                        <br>

                        📌 التصنيف:
                        {item.get('category')}

                        </p>


                        <a href="{item.get('url')}"
                        target="_blank">

                        فتح المصدر

                        </a>


                        </div>
                        """,

                        unsafe_allow_html=True

                        )



                    csv=export_csv(results)



                    st.download_button(

                        "💾 تحميل التقرير",

                        csv,

                        "report.csv",

                        "text/csv"

                    )


                else:


                    st.warning(

                    """
                    لم يتم العثور على نتائج.

                    الأسباب المحتملة:

                    - المحرك لم يجد صفحات مؤرشفة
                    - الموقع غير ظاهر لمحركات البحث
                    - الكلمة جديدة

                    """

                    )



            except Exception as e:


                st.error(

                    f"حدث خطأ:\n{e}"

                )





# ==========================================================
# HISTORY TAB
# ==========================================================


with tab2:


    st.subheader(
        "📚 آخر عمليات البحث"
    )


    history=load_history()



    if not history.empty:


        st.dataframe(

            history,

            use_container_width=True

        )


    else:


        st.info(
            "لا يوجد سجل"
        )





# ==========================================================
# STATISTICS TAB
# ==========================================================


with tab3:


    history=load_history()


    if not history.empty:


        c1,c2,c3=st.columns(3)



        c1.metric(

            "عدد النتائج",

            len(history)

        )


        c2.metric(

            "متوسط الثقة",

            f"{round(history['confidence'].mean(),1)}%"

        )


        c3.metric(

            "المصادر",

            history["url"].nunique()

        )


    else:


        st.info(

            "نفذ بحثاً أولاً"

        )



# ==========================================================
# END PROJECT
# ==========================================================
