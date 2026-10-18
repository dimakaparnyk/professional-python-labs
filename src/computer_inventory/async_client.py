"""Bounded concurrent provider requests with timeout and retry."""
import asyncio
from typing import Any
from urllib.parse import quote
import httpx


async def fetch_manufacturers(client: httpx.AsyncClient, names: list[str],
                              concurrency: int = 3, retries: int = 2,
                              timeout: float = 2.0) -> list[dict[str, Any]]:
    if not 1 <= concurrency <= 20 or len(names) > 100 or retries < 0 or timeout <= 0:
        raise ValueError("Invalid async client settings")
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch(name: str) -> dict[str, Any]:
        for attempt in range(retries + 1):
            try:
                async with semaphore, asyncio.timeout(timeout):
                    response = await client.get("/manufacturers/" + quote(name, safe=""))
                    response.raise_for_status()
                    result = response.json()
                    if not isinstance(result, dict):
                        raise ValueError("Provider response must be an object")
                    return result
            except (httpx.TransportError, TimeoutError, httpx.HTTPStatusError) as error:
                retryable = not isinstance(error, httpx.HTTPStatusError) or error.response.status_code >= 500 or error.response.status_code == 429
                if attempt == retries or not retryable:
                    raise
                await asyncio.sleep(0.01 * 2**attempt)
        raise RuntimeError("Unreachable retry state")

    tasks = [asyncio.create_task(fetch(name)) for name in names]
    try:
        return await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
