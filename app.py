# ==========================================================
# Deep Intelligence Analyzer V4
# Graduation Project Edition
# PART 1 - Core System + Database + AI Engine
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
# 1. CONFIG
# ==========================================================

APP_NAME = "Deep Intelligence Analyzer V4"
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
# 3. STYLE
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
    padding:20px;
    border-radius:12px;
    border:1px solid #374151;
    margin-bottom:15px;
}

.debug {
    background:#020617;
    padding:15px;
    border-radius:10px;
    border:1px solid #334155;
}

</style>
""",
unsafe_allow_html=True)


# ==========================================================
# 4. DATABASE
# ==========================================================


def db():

    return sqlite3.connect(
        DATABASE_FILE,
        check_same_thread=False
    )



def init_database():

    conn=db()
    cur=conn.cursor()


    cur.execute("""
    CREATE TABLE IF NOT EXISTS results(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        source TEXT,
        title TEXT,
        content TEXT,
        confidence INTEGER,
        match_type TEXT,
        analysis TEXT,
        created_at TEXT

    )
    """)



    cur.execute("""
    CREATE TABLE IF NOT EXISTS cache(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_hash TEXT UNIQUE,
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


def hash_text(text):

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()



def get_cache(query):

    conn=db()
    cur=conn.cursor()


    cur.execute(
        """
        SELECT response 
        FROM cache 
        WHERE query_hash=?
        """,
        (hash_text(query),)
    )


    row=cur.fetchone()

    conn.close()


    if row:

        data=json.loads(row[0])

        # لا نعيد النتائج الفارغة
        if len(data)>0:
            return data


    return None



def save_cache(query,data):

    # لا نخزن الفشل
    if not data:
        return


    conn=db()
    cur=conn.cursor()


    cur.execute(
        """
        INSERT OR REPLACE INTO cache
        VALUES(
        NULL,?,?,?,?
        )
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
# 6. CLEAN SYSTEM
# ==========================================================


def clean_query(text):

    text=text.strip()

    text=re.sub(
        r"[^\w@._-]",
        "",
        text
    )

    return text



# ==========================================================
# 7. IMPROVED AI ENGINE
# ==========================================================


class IntelligenceAI:


    def analyze(
        self,
        query,
        content,
        source
    ):


        score=0
        reasons=[]

        q=query.lower()
        c=content.lower()



        # Exact

        if q in c:

            score+=50

            reasons.append(
                "Exact text match"
            )



        # Mention

        if "@"+q in c:

            score+=25

            reasons.append(
                "Username mention detected"
            )



        keywords={

            "instagram":15,
            "comment":10,
            "profile":10,
            "user":5,
            "post":5

        }


        for k,v in keywords.items():

            if k in c:

                score+=v

                reasons.append(
                    "Indicator: "+k
                )



        if "instagram.com" in source:

            score+=10

            reasons.append(
                "Trusted platform source"
            )



        score=min(
            score,
            100
        )



        if score>=80:

            level="HIGH"

        elif score>=50:

            level="MEDIUM"

        else:

            level="LOW"



        return {

            "confidence":score,
            "level":level,
            "reasons":reasons

        }



AI_ENGINE=IntelligenceAI()



# ==========================================================
# END PART 1
# ========================================================== # ==========================================================
# Deep Intelligence Analyzer V4
# PART 2 - Search Engine + Smart Filter + Pipeline
# ==========================================================


# ==========================================================
# 8. HTTP SESSION
# ==========================================================

def create_session():

    session=requests.Session()

    session.headers.update({

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",

        "Accept-Language":
        "en-US,en;q=0.9"

    })

    return session




# ==========================================================
# 9. SMART MATCH ENGINE
# ==========================================================


def analyze_match(query,text):


    query=query.lower()
    text=text.lower()


    result={

        "type":"NONE",
        "score":0

    }



    # Exact

    if re.search(
        rf"(?<![\w_.]){re.escape(query)}(?![\w_.])",
        text
    ):

        result["type"]="EXACT"
        result["score"]=100

        return result




    # Mention

    if "@"+query in text:

        result["type"]="MENTION"
        result["score"]=90

        return result




    # Strong

    if query in text:

        result["type"]="STRONG"
        result["score"]=70

        return result




    # Similar

    clean=text.replace("_","")

    if query.replace("_","") in clean:

        result["type"]="POSSIBLE"
        result["score"]=40


    return result






# ==========================================================
# 10. SEARCH ENGINE V4
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

        self.debug={

            "queries":0,
            "pages":0,
            "raw_results":0,
            "filtered":0,
            "errors":[]

        }




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


        query=clean_query(query)


        if not query:

            return []



        patterns=[


            f'"{query}"',

            f'"@{query}"',

            f'"{query}" instagram',

            f'"{query}" comments',

            f'site:instagram.com "{query}"'


        ]



        self.debug["queries"]=len(patterns)



        results=[]




        def fetch(pattern,page):


            output=[]


            try:


                self.debug["pages"]+=1


                start=(page-1)*10


                url=(

                "https://duckduckgo.com/html/?q="
                +
                urllib.parse.quote(pattern)

                )



                r=self.session.get(
                    url,
                    timeout=10
                )



                if r.status_code!=200:

                    return []



                soup=BeautifulSoup(
                    r.text,
                    "html.parser"
                )



                links=soup.select(
                    ".result"
                )



                for item in links:


                    a=item.find("a")


                    if not a:

                        continue



                    href=a.get(
                        "href",
                        ""
                    )



                    title=a.text.strip()



                    snippet=item.get_text(
                        " ",
                        strip=True
                    )



                    output.append({

                        "source":href,

                        "title":title,

                        "content":snippet

                    })



            except Exception as e:

                self.debug["errors"].append(
                    str(e)
                )



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

                results.extend(
                    job.result()
                )




        self.debug["raw_results"]=len(results)




        # إزالة التكرار

        unique=[]

        seen=set()



        for r in results:


            key=r["source"]


            if key not in seen:

                seen.add(key)

                unique.append(r)





        # Smart Filtering


        filtered=[]


        for item in unique:


            combined=(

                item["title"]
                +" "
                +
                item["content"]
                +" "
                +
                item["source"]

            )



            match=analyze_match(
                query,
                combined
            )



            if match["score"]>=40:


                item["match_type"]=match["type"]

                item["match_score"]=match["score"]


                filtered.append(item)





        self.debug["filtered"]=len(filtered)



        filtered.sort(

            key=lambda x:
            x["match_score"],

            reverse=True

        )


        return filtered






# ==========================================================
# 11. PIPELINE
# ==========================================================


class Pipeline:


    def __init__(
        self,
        search,
        ai
    ):

        self.search=search
        self.ai=ai





    async def process(self,query):


        results=await self.search.search(query)


        final=[]



        for item in results:


            ai=self.ai.analyze(

                query,

                item["content"],

                item["source"]

            )



            data={

                "source":
                item["source"],


                "title":
                item["title"],


                "content":
                item["content"],


                "match_type":
                item["match_type"],


                "match_score":
                item["match_score"],


                "confidence":
                ai["confidence"],


                "level":
                ai["level"],


                "analysis":
                ai["reasons"]

            }



            conn=db()

            cur=conn.cursor()


            cur.execute(

            """
            INSERT INTO results
            VALUES(
            NULL,?,?,?,?,?,?,?,?
            )
            """,

            (

            query,

            data["source"],

            data["title"],

            data["content"],

            data["confidence"],

            data["match_type"],

            json.dumps(
                data["analysis"],
                ensure_ascii=False
            ),

            datetime.now().isoformat()

            ))


            conn.commit()

            conn.close()



            final.append(data)




        final.sort(

            key=lambda x:
            x["confidence"],

            reverse=True

        )


        return final




SEARCH_ENGINE=SearchEngineV4(
    pages=3,
    workers=5
)


PIPELINE=Pipeline(
    SEARCH_ENGINE,
    AI_ENGINE
)



# ==========================================================
# END PART 2
# ========================================================== # ==========================================================
# Deep Intelligence Analyzer V4
# PART 3 - Streamlit UI + Reports
# ==========================================================


# ==========================================================
# 12. DATA FUNCTIONS
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
# 13. HEADER
# ==========================================================


st.markdown(
    """
    <h1 class="title">
    🧠 Deep Intelligence Analyzer V4
    </h1>
    """,
    unsafe_allow_html=True
)



st.write(
"""
نظام تحليل معلومات متعدد الطبقات:
بحث + فلترة ذكية + تحليل AI + تقييم النتائج.
"""
)





# ==========================================================
# 14. SIDEBAR
# ==========================================================


with st.sidebar:


    st.header(
        "⚙️ التحكم"
    )


    SEARCH_ENGINE.pages=st.slider(

        "عمق البحث",

        1,

        10,

        3

    )


    SEARCH_ENGINE.workers=st.slider(

        "عدد المهام المتوازية",

        1,

        10,

        5

    )



    st.divider()


    st.info(
"""
المميزات:

✓ Smart Search Engine

✓ AI Scoring

✓ Match Classification

✓ Database History

✓ Cache System

✓ CSV Reports
"""
    )





# ==========================================================
# 15. TABS
# ==========================================================


tab1,tab2,tab3=st.tabs(

[
"🔎 تحليل جديد",

"📚 السجل",

"📊 الإحصائيات"

]

)





# ==========================================================
# TAB 1 SEARCH
# ==========================================================


with tab1:


    query=st.text_input(

        "أدخل البحث:",

        placeholder="example_user"

    )



    if st.button(

        "🚀 بدء التحليل",

        use_container_width=True

    ):



        if not query.strip():


            st.warning(
                "اكتب قيمة للبحث"
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



            st.session_state[
                "results"
            ]=results



            st.divider()



            debug=SEARCH_ENGINE.debug



            c1,c2,c3,c4=st.columns(4)


            c1.metric(
                "Queries",
                debug["queries"]
            )


            c2.metric(
                "Pages",
                debug["pages"]
            )


            c3.metric(
                "Raw Results",
                debug["raw_results"]
            )


            c4.metric(
                "Filtered",
                debug["filtered"]
            )





            if debug["errors"]:


                with st.expander(
                    "⚠️ الأخطاء"
                ):

                    for e in debug["errors"]:

                        st.write(e)





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
                    {item['content']}
                    </p>


                    <p>
                    🔗
                    <a href="{item['source']}" target="_blank">
                    المصدر
                    </a>
                    </p>


                    <hr>


                    Match:
                    <b>
                    {item['match_type']}
                    </b>

                    |

                    Match Score:
                    <b>
                    {item['match_score']}%
                    </b>


                    <br>


                    AI Confidence:
                    <b>
                    {item['confidence']}%
                    </b>


                    <br>


                    Level:
                    <b>
                    {item['level']}
                    </b>


                    </div>

                    """,

                    unsafe_allow_html=True

                    )



                    with st.expander(
                        "🧠 تحليل AI"
                    ):

                        for reason in item["analysis"]:

                            st.write(
                                "• "+reason
                            )





                csv=export_csv(results)


                st.download_button(

                    "💾 تحميل التقرير",

                    csv,

                    "analysis_report.csv",

                    "text/csv",

                    use_container_width=True

                )




            else:


                st.error(

                """
                لم تظهر نتائج.

                الأسباب المحتملة:

                - المحرك لم يجد صفحات مؤرشفة.
                - الموقع غير مفهرس.
                - اليوزر غير موجود علناً.
                - محرك البحث منع الطلب.

                راجع Debug لمعرفة التفاصيل.
                """

                )







# ==========================================================
# TAB 2 HISTORY
# ==========================================================


with tab2:


    st.subheader(
        "📚 آخر التحليلات"
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
# TAB 3 STATISTICS
# ==========================================================


with tab3:


    history=load_history()


    if not history.empty:


        a,b,c=st.columns(3)


        a.metric(

            "عدد العمليات",

            len(history)

        )


        b.metric(

            "متوسط الثقة",

            f"{round(history['confidence'].mean(),1)}%"

        )


        c.metric(

            "عدد المصادر",

            history["source"].nunique()

        )



    else:


        st.info(
            "لا توجد بيانات"
        )



# ==========================================================
# END V4
# 
