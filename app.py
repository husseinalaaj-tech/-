import asyncio
import json
import httpx
from typing import Dict, List


SYSTEM_CONFIG = {
    "target_url": "https://your-target-system.com/api/v1/redeem",

    "headers": {
        "User-Agent": "My-Test-Client/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json"
    },

    "timeout": 10.0,

    # عدد المحاولات عند حدوث خطأ مؤقت
    "retries": 3
}


async def check_single_code_api(
    client: httpx.AsyncClient,
    code: str,
    config: Dict
) -> Dict:

    payload = {
        "code": code
    }

    retries = config.get("retries", 3)

    for attempt in range(retries):

        try:
            response = await client.post(
                config["target_url"],
                json=payload,
                headers=config["headers"],
                timeout=config["timeout"]
            )

            # التحقق من حالة HTTP
            if response.status_code >= 500:
                raise httpx.HTTPError(
                    f"Server error {response.status_code}"
                )


            # محاولة قراءة JSON
            try:
                data = response.json()

                status = str(
                    data.get("status", "unknown")
                ).lower()

                return {
                    "code": code,
                    "status": status,
                    "http_status": response.status_code,
                    "data": data
                }


            except json.JSONDecodeError:

                text = response.text.lower()

                return {
                    "code": code,
                    "status":
                        "valid"
                        if "success" in text
                        else "invalid",

                    "http_status": response.status_code,
                    "message": response.text[:200]
                }


        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.HTTPError
        ) as e:

            if attempt == retries - 1:
                return {
                    "code": code,
                    "status": "error",
                    "message": str(e)
                }

            # انتظار قبل المحاولة التالية
            await asyncio.sleep(
                1 + attempt
            )


        except Exception as e:

            return {
                "code": code,
                "status": "error",
                "message": str(e)
            }



async def batch_process_codes(
    codes: List[str],
    config: Dict,
    max_concurrency: int = 10
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

        results = await asyncio.gather(
            *tasks
        )

        return results



async def main():

    test_codes = [
        "TEST-001",
        "TEST-002",
        "TEST-003",
        "TEST-004"
    ]


    print(
        f"[*] Testing {len(test_codes)} items..."
    )


    results = await batch_process_codes(
        test_codes,
        SYSTEM_CONFIG,
        max_concurrency=10
    )


    print("\n--- RESULTS ---")

    for result in results:
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )



if __name__ == "__main__":
    asyncio.run(main())
