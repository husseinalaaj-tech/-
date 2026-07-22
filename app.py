# ==========================================================
# Deep Intelligence Analyzer V4
# Graduation Project Edition
# Part 1/4
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
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from bs4 import BeautifulSoup
except:
    BeautifulSoup = None


# ==========================================================
# CONFIG
# ==========================================================

APP_NAME = "Deep Intelligence Analyzer V4"

DATABASE_FILE = "intelligence_v4.db"


# ==========================================================
# STREAMLIT CONFIG
# ==========================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🧠",
    layout="wide"
)


# ==========================================================
# STYLE
# ==========================================================

st.markdown("""
<style>

.stApp{
background:#0b0f19;
color:white;
}

.title{
text-align:center;
font-size:40px;
font-weight:900;
color:#3b82f6;
}

.card{
background:#111827;
padding:20px;
border-radius:15px;
border:1px solid #263244;
margin:15px 0;
}

</style>
""", unsafe_allow_html=True)



# ==========================================================
# DATABASE CONNECTION
# ==========================================================

def db_connection():

    conn = sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )

    return conn



# ==========================================================
# DATABASE INIT (FIXED)
# ==========================================================

def init_database():

    conn = db_connection()

    cur = conn.cursor()


    cur.execute("""
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



    cur.execute("""
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
# CACHE SYSTEM
# ==========================================================


def hash_text(text):

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()



def get_cache(query):

    conn=db_connection()

    cur=conn.cursor()


    cur.execute(
        """
        SELECT response 
        FROM cache
        WHERE hash=?
        """,
        (
            hash_text(query),
        )
    )


    row=cur.fetchone()

    conn.close()


    if row:

        try:
            return json.loads(row[0])

        except:
            return None


    return None




def save_cache(query,data):

    conn=db_connection()

    cur=conn.cursor()


    cur.execute(
        """
        INSERT OR REPLACE INTO cache
        (
        hash,
        query,
        response,
        created_at
        )

        VALUES
        (?,?,?,?)
        """,

        (
            hash_text(query),
            query,
            json.dumps(
                data,
                ensure_ascii=False
            ),
            datetime.now().isoformat()
        )
    )


    conn.commit()
    conn.close()



# ==========================================================
# TEXT CLEANER
# ==========================================================


def clean_text(text):

    if not text:
        return ""

    text=str(text)

    text=re.sub(
        r"[^\w\s@.-]",
        "",
        text
    )

    return text.strip()



# ==========================================================
# HTTP SESSION
# ==========================================================


def create_session():

    session=requests.Session()


    session.headers.update({

        "User-Agent":
        "Mozilla/5.0 Chrome/120 Safari/537.36"

    })


    return session

# ==========================================================
# PART 2/4
# AI ENGINE + RESULT STORAGE
# ==========================================================


# ==========================================================
# SAVE RESULTS
# ==========================================================

def save_result(
    query,
    source,
    content,
    ai_data
):

    conn=db_connection()

    cur=conn.cursor()


    cur.execute(
        """
        INSERT INTO results
        (
        query,
        source,
        content,
        confidence,
        category,
        analysis,
        created_at
        )

        VALUES
        (?,?,?,?,?,?,?)
        """,

        (
            query,
            source,
            content,
            ai_data["confidence"],
            ai_data["category"],
            json.dumps(
                ai_data["analysis"],
                ensure_ascii=False
            ),
            datetime.now().isoformat()
        )
    )


    conn.commit()
    conn.close()



# ==========================================================
# ADVANCED LOCAL AI ENGINE
# ==========================================================


class IntelligenceAI:


    def __init__(self):

        self.version="AI-V4"



    def keyword_analysis(self,text):

        keywords={

            "profile":10,
            "account":10,
            "user":5,
            "comment":15,
            "message":10,
            "post":10,
            "instagram":20,
            "social":5

        }


        score=0

        reasons=[]


        lower=text.lower()



        for word,value in keywords.items():

            if word in lower:

                score+=value

                reasons.append(
                    f"تم العثور على مؤشر: {word}"
                )



        return score,reasons




    def analyze(
        self,
        query,
        content
    ):


        query=query.lower()

        content=content.lower()



        score=0

        reasons=[]



        # تطابق مباشر

        if query in content:

            score+=50

            reasons.append(
                "تطابق مباشر للنص"
            )



        # تحليل الكلمات

        k_score,k_reason = self.keyword_analysis(
            content
        )


        score+=k_score

        reasons.extend(k_reason)



        # حجم المحتوى

        if len(content)>500:

            score+=15

            reasons.append(
                "محتوى طويل وغني"
            )


        elif len(content)>100:

            score+=8

            reasons.append(
                "محتوى متوسط"
            )



        if score>100:

            score=100




        if score>=75:

            category="HIGH"

        elif score>=45:

            category="MEDIUM"

        else:

            category="LOW"




        return {

            "confidence":score,

            "category":category,

            "analysis":reasons

        }




AI_ENGINE=IntelligenceAI()



# ==========================================================
# SOURCE QUALITY SCORE
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


    medium=[

        "reddit.com",
        "github.com",
        "medium.com"

    ]



    for site in trusted:

        if site in url:

            score+=30



    for site in medium:

        if site in url:

            score+=15



    if url.startswith("https"):

        score+=10



    return min(score,100)




# ==========================================================
# REMOVE DUPLICATES
# ==========================================================


def remove_duplicates(results):


    final=[]

    seen=set()



    for item in results:


        key=(
            item.get("source","")
            +
            item.get("content","")
        )



        if key not in seen:

            seen.add(key)

            final.append(item)



    return final

# ==========================================================
# PART 3/4
# SEARCH ENGINE + PIPELINE
# ==========================================================


# ==========================================================
# ONLINE SEARCH ENGINE
# ==========================================================


class SearchEngineV4:


    def __init__(
        self,
        pages=3,
        workers=5
    ):

        self.pages=pages

        self.workers=workers

        self.session=create_session()



    async def search(self,query):


        cached=get_cache(query)


        if cached:

            return cached



        loop=asyncio.get_event_loop()


        result=await loop.run_in_executor(

            None,

            self.deep_search,

            query

        )



        save_cache(
            query,
            result
        )


        return result




    def deep_search(self,query):


        safe_query=clean_text(query)



        if not safe_query:

            return []



        patterns=[

            f'"{safe_query}"',

            f'"{safe_query}" profile',

            f'"{safe_query}" comments',

            f'site:instagram.com "{safe_query}"'

        ]



        results=[]



        def fetch(pattern,page):


            output=[]


            try:

                start=(page-1)*10+1


                url=(

                "https://search.yahoo.com/search?"

                +

                urllib.parse.urlencode({

                    "p":pattern,

                    "b":start

                })

                )



                response=self.session.get(

                    url,

                    timeout=10

                )



                if response.status_code!=200:

                    return []



                if BeautifulSoup is None:

                    return []



                soup=BeautifulSoup(

                    response.text,

                    "html.parser"

                )



                blocks=soup.find_all(

                    "div",

                    class_="compTitle"

                )



                for block in blocks:


                    link=block.find("a")


                    if not link:

                        continue



                    href=link.get(

                        "href",

                        ""

                    )


                    title=link.text.strip()



                    parent=block.find_next_sibling()



                    content=""


                    if parent:

                        content=parent.text.strip()



                    output.append({

                        "source":href,

                        "title":title,

                        "content":content,

                        "source_score":

                        source_score(href)

                    })


            except Exception:


                pass



            return output





        jobs=[]


        with ThreadPoolExecutor(
            max_workers=self.workers
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

                try:

                    results.extend(
                        job.result()
                    )

                except:

                    pass





        results=remove_duplicates(results)



        return results






# ==========================================================
# INTELLIGENCE PIPELINE
# ==========================================================


class IntelligencePipeline:


    def __init__(
        self,
        search_engine,
        ai_engine
    ):

        self.search_engine=search_engine

        self.ai_engine=ai_engine





    async def process(self,query):


        results=await self.search_engine.search(
            query
        )


        final=[]



        for item in results:


            ai=self.ai_engine.analyze(

                query,

                item.get(
                    "content",
                    ""
                )

            )



            data={


                "source":

                item.get(
                    "source",
                    ""
                ),



                "title":

                item.get(
                    "title",
                    ""
                ),



                "content":

                item.get(
                    "content",
                    ""
                ),



                "source_score":

                item.get(
                    "source_score",
                    0
                ),



                "confidence":

                ai["confidence"],



                "category":

                ai["category"],



                "analysis":

                ai["analysis"]

            }



            save_result(

                query,

                data["source"],

                data["content"],

                ai

            )



            final.append(data)



        final.sort(

            key=lambda x:

            x["confidence"],

            reverse=True

        )


        return final





SEARCH_ENGINE=SearchEngineV4()

PIPELINE=IntelligencePipeline(

    SEARCH_ENGINE,

    AI_ENGINE

)

# ==========================================================
# PART 4/4
# STREAMLIT UI + REPORTS
# ==========================================================


# ==========================================================
# HISTORY
# ==========================================================

def load_history():

    conn=db_connection()

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
# EXPORT
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
# HEADER
# ==========================================================


st.markdown(
    """
    <div class="title">
    🧠 Deep Intelligence Analyzer V4
    </div>
    """,
    unsafe_allow_html=True
)


st.write(
    """
    نظام تحليل ذكي متعدد الطبقات يحتوي على:
    
    ✓ قاعدة بيانات  
    ✓ نظام Cache  
    ✓ محرك AI محلي  
    ✓ تقييم المصادر  
    ✓ تحليل النتائج  
    """
)



# ==========================================================
# SIDEBAR
# ==========================================================


with st.sidebar:


    st.header("⚙️ الإعدادات")


    depth=st.slider(

        "عمق البحث",

        1,

        10,

        3

    )


    SEARCH_ENGINE.pages=depth



    st.divider()


    st.info(
        """
        Deep Intelligence Analyzer V4
        
        Architecture:
        
        • SQLite Database
        • AI Engine
        • Cache System
        • Search Pipeline
        """
    )





# ==========================================================
# TABS
# ==========================================================


tab1,tab2,tab3 = st.tabs(

    [

    "🔎 تحليل جديد",

    "📚 السجل",

    "📊 الإحصائيات"

    ]

)



# ==========================================================
# SEARCH TAB
# ==========================================================


with tab1:


    query=st.text_input(

        "أدخل النص المراد تحليله",

        placeholder="example"

    )



    if st.button(

        "🚀 بدء التحليل",

        use_container_width=True

    ):


        if not query.strip():


            st.warning(
                "أدخل قيمة للبحث"
            )


        else:


            with st.spinner(

                "جاري التحليل..."

            ):


                results=asyncio.run(

                    PIPELINE.process(
                        query
                    )

                )



            st.session_state["results"]=results



            if results:


                st.success(

                    f"تم العثور على {len(results)} نتيجة"

                )



                for item in results:


                    st.markdown(

                    f"""

                    <div class="card">

                    <h3>

                    {item['title']}

                    </h3>


                    <p>

                    {item['content'][:500]}

                    </p>


                    <hr>


                    🔗 المصدر:

                    {item['source']}


                    <br>


                    🤖 الثقة:

                    {item['confidence']}%


                    <br>


                    📊 جودة المصدر:

                    {item['source_score']}


                    <br>


                    🏷️ التصنيف:

                    {item['category']}



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


                st.error(

                    "لم يتم العثور على نتائج"

                )





# ==========================================================
# HISTORY TAB
# ==========================================================


with tab2:


    st.subheader(
        "📚 آخر العمليات"
    )


    history=load_history()



    if not history.empty:


        st.dataframe(

            history,

            use_container_width=True

        )


    else:


        st.info(

            "لا توجد بيانات"

        )





# ==========================================================
# STATISTICS TAB
# ==========================================================


with tab3:


    history=load_history()


    if not history.empty:


        c1,c2,c3=st.columns(3)



        c1.metric(

            "عدد العمليات",

            len(history)

        )


        c2.metric(

            "متوسط الثقة",

            f"{round(history['confidence'].mean(),1)}%"

        )


        c3.metric(

            "المصادر",

            history["source"].nunique()

        )



    else:


        st.info(

            "لا توجد إحصائيات بعد"

        )
