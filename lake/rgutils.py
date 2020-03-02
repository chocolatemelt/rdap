import json
import os
import yaml

rg_seasons = []

with open(os.path.join(os.path.dirname(__file__), "static/seasons.json")) as inf:
    rg_seasons = json.load(inf)


def get_season():
    return rg_seasons[0]["id"]


def get_last_season():
    return rg_seasons[2]["id"]
