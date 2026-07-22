# ==========================================================
# Deep Intelligence Analyzer V4 FINAL
# PART 2 - Search Engine + Smart Filter + Pipeline
# ==========================================================


# ==========================================================
# HTTP SESSION
# ==========================================================

def create_session():

    session = requests.Session()

    session.headers.update({

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",

        "Accept-Language":
        "en-US,en;q=0.9"

    })

    return session



# ==========================================================
# SMART MATCH SYSTEM
# ==========================================================


def smart_match(query, text):

    query=query.lower()

    text=text.lower()


    # Exact match

    if re.search(
        rf"(?<![\w_.]){re.escape(query)}(?![\w_.])",
        text
    ):

        return {

            "type":"EXACT",

            "score":100

        }



    # Mention

    if "@"+query in text:

        return {

            "type":"MENTION",

            "score":90

        }



    # Strong

    if query in text:

        return {

            "type":"STRONG",

            "score":70

        }



    # Possible

    if query.replace("_","") in text.replace("_",""):

        return {

            "type":"POSSIBLE",

            "score":40

        }



    return {

        "type":"NONE",

        "score":0

    }





# ==========================================================
# SEARCH ENGINE
# ==========================================================


class SearchEngineV4:


    def __init__(self):

        self.pages=3

        self.workers=5

        self.session=create_session()


        self.debug={

            "patterns":0,

            "pages":0,

            "raw":0,

            "filtered":0,

            "errors":[]

        }





    async def search(self,query):


        cached=get_cache(query)


        if cached:

            return cached



        loop=asyncio.get_event_loop()


        results=await loop.run_in_executor(

            None,

            self._search,

            query

        )


        save_cache(
            query,
            results
        )


        return results





    def _search(self,query):


        query=clean_query(query)


        if not query:

            return []



        patterns=[

            f'"{query}"',

            f'"@{query}"',

            f'"{query}" comments',

            f'"{query}" profile',

            f'site:instagram.com "{query}"'

        ]



        self.debug["patterns"]=len(patterns)



        raw=[]





        def fetch(pattern,page):


            data=[]


            try:


                self.debug["pages"]+=1



                url=(

                    "https://duckduckgo.com/html/?q="

                    +

                    urllib.parse.quote(pattern)

                )



                response=self.session.get(

                    url,

                    timeout=10

                )



                if response.status_code != 200:

                    return []



                if BeautifulSoup is None:

                    return []



                soup=BeautifulSoup(

                    response.text,

                    "html.parser"

                )



                items=soup.select(
                    ".result"
                )



                for item in items:


                    link=item.find(
                        "a",
                        class_="result__a"
                    )


                    if not link:

                        continue



                    title=link.text.strip()


                    href=link.get(
                        "href",
                        ""
                    )


                    snippet=item.get_text(
                        " ",
                        strip=True
                    )



                    data.append({

                        "source":href,

                        "title":title,

                        "content":snippet

                    })



            except Exception as e:


                self.debug["errors"].append(
                    str(e)
                )


            return data






        tasks=[]


        with ThreadPoolExecutor(
            max_workers=self.workers
        ) as executor:


            for pattern in patterns:


                for page in range(
                    1,
                    self.pages+1
                ):


                    tasks.append(

                        executor.submit(
                            fetch,
                            pattern,
                            page
                        )

                    )



            for task in as_completed(tasks):

                raw.extend(
                    task.result()
                )




        self.debug["raw"]=len(raw)





        # إزالة التكرار

        unique=[]

        seen=set()



        for item in raw:


            if item["source"] not in seen:


                seen.add(
                    item["source"]
                )

                unique.append(item)





        # فلترة ذكية

        filtered=[]



        for item in unique:


            combined=(

                item["title"]

                +

                " "

                +

                item["content"]

                +

                " "

                +

                item["source"]

            )



            match=smart_match(

                query,

                combined

            )



            if match["score"]>=40:


                item["match_type"]=match["type"]

                item["match_score"]=match["score"]


                filtered.append(item)





        self.debug["filtered"]=len(filtered)



        filtered.sort(

            key=lambda x:x["match_score"],

            reverse=True

        )


        return filtered





# ==========================================================
# PIPELINE
# ==========================================================


class IntelligencePipeline:


    def __init__(self,search,ai):

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

            (

            query,

            source,

            title,

            content,

            confidence,

            match_type,

            analysis,

            created_at

            )

            VALUES(?,?,?,?,?,?,?,?)

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

            key=lambda x:x["confidence"],

            reverse=True

        )


        return final





SEARCH_ENGINE=SearchEngineV4()


PIPELINE=IntelligencePipeline(

    SEARCH_ENGINE,

    AI_ENGINE

)


# ==========================================================
# END PART 2
# ========================================================== # ==========================================================
# Deep Intelligence Analyzer V4 FINAL
# PART 2 - Search Engine + Smart Filter + Pipeline
# ==========================================================


# ==========================================================
# HTTP SESSION
# ==========================================================

def create_session():

    session = requests.Session()

    session.headers.update({

        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",

        "Accept-Language":
        "en-US,en;q=0.9"

    })

    return session



# ==========================================================
# SMART MATCH SYSTEM
# ==========================================================


def smart_match(query, text):

    query=query.lower()

    text=text.lower()


    # Exact match

    if re.search(
        rf"(?<![\w_.]){re.escape(query)}(?![\w_.])",
        text
    ):

        return {

            "type":"EXACT",

            "score":100

        }



    # Mention

    if "@"+query in text:

        return {

            "type":"MENTION",

            "score":90

        }



    # Strong

    if query in text:

        return {

            "type":"STRONG",

            "score":70

        }



    # Possible

    if query.replace("_","") in text.replace("_",""):

        return {

            "type":"POSSIBLE",

            "score":40

        }



    return {

        "type":"NONE",

        "score":0

    }





# ==========================================================
# SEARCH ENGINE
# ==========================================================


class SearchEngineV4:


    def __init__(self):

        self.pages=3

        self.workers=5

        self.session=create_session()


        self.debug={

            "patterns":0,

            "pages":0,

            "raw":0,

            "filtered":0,

            "errors":[]

        }





    async def search(self,query):


        cached=get_cache(query)


        if cached:

            return cached



        loop=asyncio.get_event_loop()


        results=await loop.run_in_executor(

            None,

            self._search,

            query

        )


        save_cache(
            query,
            results
        )


        return results





    def _search(self,query):


        query=clean_query(query)


        if not query:

            return []



        patterns=[

            f'"{query}"',

            f'"@{query}"',

            f'"{query}" comments',

            f'"{query}" profile',

            f'site:instagram.com "{query}"'

        ]



        self.debug["patterns"]=len(patterns)



        raw=[]





        def fetch(pattern,page):


            data=[]


            try:


                self.debug["pages"]+=1



                url=(

                    "https://duckduckgo.com/html/?q="

                    +

                    urllib.parse.quote(pattern)

                )



                response=self.session.get(

                    url,

                    timeout=10

                )



                if response.status_code != 200:

                    return []



                if BeautifulSoup is None:

                    return []



                soup=BeautifulSoup(

                    response.text,

                    "html.parser"

                )



                items=soup.select(
                    ".result"
                )



                for item in items:


                    link=item.find(
                        "a",
                        class_="result__a"
                    )


                    if not link:

                        continue



                    title=link.text.strip()


                    href=link.get(
                        "href",
                        ""
                    )


                    snippet=item.get_text(
                        " ",
                        strip=True
                    )



                    data.append({

                        "source":href,

                        "title":title,

                        "content":snippet

                    })



            except Exception as e:


                self.debug["errors"].append(
                    str(e)
                )


            return data






        tasks=[]


        with ThreadPoolExecutor(
            max_workers=self.workers
        ) as executor:


            for pattern in patterns:


                for page in range(
                    1,
                    self.pages+1
                ):


                    tasks.append(

                        executor.submit(
                            fetch,
                            pattern,
                            page
                        )

                    )



            for task in as_completed(tasks):

                raw.extend(
                    task.result()
                )




        self.debug["raw"]=len(raw)





        # إزالة التكرار

        unique=[]

        seen=set()



        for item in raw:


            if item["source"] not in seen:


                seen.add(
                    item["source"]
                )

                unique.append(item)





        # فلترة ذكية

        filtered=[]



        for item in unique:


            combined=(

                item["title"]

                +

                " "

                +

                item["content"]

                +

                " "

                +

                item["source"]

            )



            match=smart_match(

                query,

                combined

            )



            if match["score"]>=40:


                item["match_type"]=match["type"]

                item["match_score"]=match["score"]


                filtered.append(item)





        self.debug["filtered"]=len(filtered)



        filtered.sort(

            key=lambda x:x["match_score"],

            reverse=True

        )


        return filtered





# ==========================================================
# PIPELINE
# ==========================================================


class IntelligencePipeline:


    def __init__(self,search,ai):

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

            (

            query,

            source,

            title,

            content,

            confidence,

            match_type,

            analysis,

            created_at

            )

            VALUES(?,?,?,?,?,?,?,?)

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

            key=lambda x:x["confidence"],

            reverse=True

        )


        return final





SEARCH_ENGINE=SearchEngineV4()


PIPELINE=IntelligencePipeline(

    SEARCH_ENGINE,

    AI_ENGINE

)


# ==========================================================
# END PART 2
# 
