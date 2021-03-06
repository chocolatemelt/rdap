import json
import os
import requests
import sys
import urllib
import yaml

config = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "../config.yml")))

RGAPI_KEY = config["riot"]["api_key"]
RGAPI_REGION = config["riot"]["region"]


def auth_headers():
    return {
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Riot-Token": RGAPI_KEY,
        "Accept-Language": "en-US,en;q=0.5",
    }


def get(route):
    return requests.get(
        f"https://{RGAPI_REGION}.api.riotgames.com{route}", headers=auth_headers()
    )


def get_eaid(summoner_name):
    res = get(f"/lol/summoner/v4/summoners/by-name/{urllib.parse.quote(summoner_name)}")
    return res.json()["accountId"]


def get_matchlist(eaid):
    res = get(f"/lol/match/v4/matchlists/by-account/{eaid}")
    return res.json()["matches"]


def get_match(match_id):
    res = get(f"/lol/match/v4/matches/{match_id}")
    return res.json()


if __name__ == "__main__":
    SUMMONER = sys.argv[1]
    if len(sys.argv) > 2:
        print("too many arguments! did you forget to wrap the name in quotes?")
        sys.exit(1)
    print(f"getting data for {SUMMONER}...")
    print(f"{SUMMONER}'s encrypted account ID is {get_eaid(SUMMONER)}")
    print(
        json.dumps(get_match(get_matchlist(get_eaid(SUMMONER))[0]["gameId"]), indent=2)
    )

