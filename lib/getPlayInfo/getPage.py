from typing import *
import requests
import lib.util as util
import lib.types as types

cache = {}


def get(video: str, cookie: str) -> list[types.VideoPart]:
    logger = util.getLogger("download page")
    url = util.getPageUrl(video)
    headers = util.getHeader(cookie, url)
    if url in cache:
        logger.info(f"get page from cache: {url}")
        return cache[url]
    try:
        logger.info(f"request page url: {url}, headers: {headers}")
        response = requests.get(url, headers=headers, timeout=util.config.timeout)
        logger.info(f"response status code: {response.status_code}")
        assert response.status_code // 100 == 2
        html = response.text
    except Exception as e:
        logger.warning(f"Can't get page response with error {util.errorLogInfo(e)}")
        util.dialog.showerror(
            "错误",
            f"请求错误，无法获取页面信息\n{util.errorLogInfo(e)}",
        )
        return

    cache[url] = html
    return html
