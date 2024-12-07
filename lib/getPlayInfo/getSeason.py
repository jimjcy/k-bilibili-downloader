from typing import *
import re
import json
import lib.util as util
import lib.types as types
from . import getPage
from . import api
import requests


def get(video: str, cookie: str) -> list[types.VideoPart]:
    logger = util.getLogger("AnalyzingPageSeasonInfo")
    html = getPage.get(video, cookie)

    def findSeasonId(d: dict | list) -> int | None:
        for i in d if isinstance(d, dict) else range(len(d)):
            if i == "season_id" and type(d[i]) == int:
                return d[i]
            elif type(d[i]) == dict or type(d[i]) == list:
                r = findSeasonId(d[i])
                if r:
                    return r

    try:
        logger.info("start parse page")
        seasonId: int | None = None
        for i in [
            re.compile(r"window.__INITIAL_STATE__\s*=\s*(\{.*?\});", re.S),
        ]:
            try:
                seasonId = findSeasonId(json.loads(re.findall(i, html)[0]))
                assert seasonId
            except Exception as e:
                print(e)
                continue
            else:
                break

        if not seasonId:
            logger.info("Can't find season_id")
            raise Exception("Can't find season_id")
        res = requests.get(
            "https://api.bilibili.com/pgc/web/season/section",
            params={
                "season_id": seasonId,
            },
            timeout=util.config.timeout,
            headers=util.getHeader(
                cookie,
                util.getPageUrl(video),
                Accept="application/json, text/plain, */*",
            ),
        )
        res.raise_for_status()
        return [
            types.VideoPart(
                title=i["long_title"],
                playinfo=util.toCallback(
                    api.getPlayInfo,
                    {
                        "aid": i["aid"],
                        "cid": i["cid"],
                    },
                    cookie,
                ),
            )
            for i in res.json()["result"]["main_section"]["episodes"]
        ]
    except Exception:
        return []
