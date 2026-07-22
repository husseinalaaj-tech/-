import streamlit as st
import asyncio
import json
import httpx


st.set_page_config(
    page_title="API Code Validator",
    page_icon="🧠",
    layout="wide"
)


st.title("🧠 API Validation Tester")
st.write("نظام اختبار API باستخدام Async HTTP Client")


SYSTEM_CONFIG = {
    "target_url": "https://your-target-system.com/api/v1/redeem",

    "headers": {
        "User-Agent": "My-Test-Client/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json"
    },

    "timeout": 10.0,
    "retries": 3
}



async def check_single_code_api(client, code, config):

    payload = {
        "code": code
    }


    for attempt in range(config["retries"]):

        try:

            response = await client.post(
                config["target_url"],
                json=payload,
                headers=config["headers"],
                timeout=config["timeout"]
            )


            try:

                data = response.json()

                return {
                    "code": code,
                    "status": data.get(
                        "status",
                        "unknown"
                    ),
                    "http_status": response.status_code,
                    "data": data
                }


            except json.JSONDecodeError:

                return {
                    "code": code,
                    "status": "text_response",
                    "http_status": response.status_code,
                    "message": response.text[:200]
                }


        except Exception as e:

            if attempt == config["retries"] - 1:

                return {
                    "code": code,
                    "status": "error",
                    "message": str(e)
                }


            await asyncio.sleep(1)



async def batch_process_codes(
    codes,
    config,
    max_concurrency=10
):

    semaphore = asyncio.Semaphore(
        max_concurrency
    )


    async with httpx.AsyncClient(
        http2=True
    ) as client:


        async def worker(code):

            async with semaphore:

                return await check_single_code_api(
                    client,
                    code,
                    config
                )


        tasks = [
            worker(code)
            for code in codes
        ]


        return await asyncio.gather(
            *tasks
        )



async def run_test(codes):

    results = await batch_process_codes(
        codes,
        SYSTEM_CONFIG,
        max_concurrency=10
    )

    return results



# ---------------- UI ----------------


st.sidebar.header("⚙️ Settings")


SYSTEM_CONFIG["target_url"] = st.sidebar.text_input(
    "API URL",
    SYSTEM_CONFIG["target_url"]
)


codes_input = st.text_area(
    "أدخل الأكواد (كل كود في سطر):",
    value="TEST-001\nTEST-002\nTEST-003",
    height=150
)



if st.button("🚀 بدء الاختبار"):


    codes = [
        x.strip()
        for x in codes_input.split("\n")
        if x.strip()
    ]


    if not codes:

        st.warning(
            "أدخل كود واحد على الأقل"
        )

    else:

        with st.spinner(
            "جاري الاتصال بالـ API..."
        ):

            results = asyncio.run(
                run_test(codes)
            )


        st.success(
            "اكتمل الاختبار"
        )


        st.subheader(
            "📋 النتائج"
        )


        for result in results:

            if result.get("status") in [
                "valid",
                "success"
            ]:

                st.success(
                    json.dumps(
                        result,
                        indent=2,
                        ensure_ascii=False
                    )
                )

            else:

                st.error(
                    json.dumps(
                        result,
                        indent=2,
                        ensure_ascii=False
                    )
                )
