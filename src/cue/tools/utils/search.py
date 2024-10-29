import json
import logging
import time
from itertools import islice
from typing import Union

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


DUCKDUCKGO_MAX_ATTEMPTS = 3


# Reference: https://github.com/Significant-Gravitas/AutoGPT/blob/master/forge/forge/components/web/search.py
def duckduckgo_search(query: str, num_results: int = 8) -> str:
    search_results = []
    attempts = 0

    while attempts < DUCKDUCKGO_MAX_ATTEMPTS:
        if not query:
            return json.dumps(search_results)

        # https://github.com/deedy5/duckduckgo_search
        results = DDGS().text(query)
        search_results = list(islice(results, num_results))

        if search_results:
            break

        time.sleep(1)
        attempts += 1

    search_results = [
        {
            "title": r["title"],
            "url": r["href"],
            **({"snippet": r["body"]} if r.get("body") else {}),
        }
        for r in search_results
    ]
    # res = json.dumps(search_results, ensure_ascii=False, indent=4)
    # print(f"res: {res}")
    final_search_results = safe_google_results(search_results)
    return final_search_results


def safe_google_results(results: Union[str, list]) -> str:
    """
    Return the Google search results in a safe format.

    Args:
        results (str | list): The search results.

    Returns:
        str: The results of the search in JSON format.
    """
    if isinstance(results, list):
        # Ensure that only string types within each dictionary result are encoded
        encoded_list = []
        for result in results:
            if isinstance(result, dict):
                encoded_dict = {
                    k: (v.encode("utf-8", "ignore").decode("utf-8") if isinstance(v, str) else v)
                    for k, v in result.items()
                }
                encoded_list.append(encoded_dict)
            else:
                encoded_list.append(result)
        safe_message = json.dumps(encoded_list, ensure_ascii=False)
    else:
        safe_message = results.encode("utf-8", "ignore").decode("utf-8")

    return safe_message


def search_news(query) -> list[str]:
    results = DDGS().news(keywords=query, region="wt-wt", safesearch="off", timelimit="m", max_results=20)
    processed_results = []
    for result in results:
        if "image" in result:
            del result["image"]
        processed_results.append(result)

    return results


if __name__ == "__main__":
    q = "today's major AI news"
    res = duckduckgo_search(query=q)
    print(f"result:\n{res}")
