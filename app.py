import streamlit as st
import asyncio
import random
import json
import httpx


st.set_page_config(
    page_title="Secure Code System",
    page_icon="🔑",
    layout="wide"
)


st.markdown("""
<style>
.stApp {
    background:#0b0f19;
    color:white;
}

.title {
    text-align:center;
    font-size:35px;
    font-weight:bold;
    color:#3b82f6;
}

.code {
    background:#111827;
    padding:10px;
    border-radius:8px;
    font-family:monospace;
    margin:5px;
}
</style>
""", unsafe_allow_html=True)



# ==========================
# Code Generator
# ==========================

ALLOWED_CHARS = "BCDFGHJKMNPQRVWXYZ2346789"


def generate_single_code():

    groups = []

    for _ in range(5):

        group = "".join(
            random.choice(ALLOWED_CHARS)
            for _ in range(5)
        )

        groups.append(group)

    return "-".join(groups)



def generate_codes(number):

    return [
        generate_single_code()
        for _ in range(number)
    ]



# ==========================
# API Checker
# ==========================

async def check_code(client, code, api_url):

    try:

        response = await client.post(
            api_url,
            json={
                "code": code
            },
            timeout=10
        )


        try:

            data = response.json()

            return {
                "code": code,
                "status": data.get(
                    "status",
                    "unknown"
                ),
                "response": data
            }


        except:

            return {
                "code": code,
                "status": "text",
                "response": response.text[:200]
            }



    except Exception as e:

        return {
            "code": code,
            "status": "error",
            "response": str(e)
        }




async def run_checker(codes, api_url):

    async with httpx.AsyncClient() as client:

        tasks = [
            check_code(
                client,
                code,
                api_url
            )
            for code in codes
        ]

        return await asyncio.gather(*tasks)



# ==========================
# Interface
# ==========================


st.markdown(
    "<div class='title'>🔑 Secure Code Generator System</div>",
    unsafe_allow_html=True
)


tab1, tab2 = st.tabs(
    [
        "🔑 توليد الأكواد",
        "🌐 فحص API الخاص بك"
    ]
)



# ---------- Generator ----------

with tab1:

    st.subheader(
        "مولد الأكواد"
    )


    amount = st.number_input(
        "عدد الأكواد",
        1,
        10000,
        20
    )


    if st.button(
        "🚀 توليد",
        use_container_width=True
    ):

        codes = generate_codes(amount)

        st.session_state.codes = codes


        st.success(
            f"تم توليد {amount} كود"
        )


    if "codes" in st.session_state:

        for c in st.session_state.codes:

            st.markdown(
                f"<div class='code'>{c}</div>",
                unsafe_allow_html=True
            )


        download = "\n".join(
            st.session_state.codes
        )


        st.download_button(
            "⬇️ حفظ الأكواد",
            download,
            "codes.txt"
        )



# ---------- API ----------

with tab2:

    st.subheader(
        "فحص عبر API نظامك"
    )


    api_url = st.text_input(
        "رابط API الخاص بك",
        "https://your-domain.com/api/check"
    )


    input_codes = st.text_area(
        "الأكواد",
        value="\n".join(
            st.session_state.get(
                "codes",
                []
            )
        )
    )


    if st.button(
        "⚡ بدء الفحص",
        use_container_width=True
    ):


        codes = [
            x.strip()
            for x in input_codes.split("\n")
            if x.strip()
        ]


        if not codes:

            st.warning(
                "لا توجد أكواد"
            )

        else:

            with st.spinner(
                "جاري الفحص..."
            ):

                results = asyncio.run(
                    run_checker(
                        codes,
                        api_url
                    )
                )


            st.success(
                "انتهى الفحص"
            )


            for r in results:

                st.json(r)



# ---------- Info ----------


with st.sidebar:

    st.header(
        "📌 البنية"
    )

    st.write(
        """
التنسيق:

XXXXX-XXXXX-XXXXX-XXXXX-XXXXX


الرموز:

B C D F G H J K M N P Q R V W X Y Z

2 3 4 6 7 8 9
"""
    )
