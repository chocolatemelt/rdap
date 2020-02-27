import json
import os
import requests

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    versions = {}
    reverse_lut = {}

    print("getting latest valid ddragon version...")
    with open(os.path.join(here, "versions.json")) as inf:
        versions = json.load(inf)

    print("getting latest ddragon champion list...")
    res = requests.get(
        f"http://ddragon.leagueoflegends.com/cdn/{versions[0]}/data/en_US/champion.json"
    )
    champions = res.json()["data"]

    print("creating reverse lookup...")
    for c in champions:
        key = champions[c]["key"]
        reverse_lut[key] = champions[c]

    print("saving reverse lookup to champions.json...")
    with open(os.path.join(here, "champions.json"), "w") as outf:
        json.dump(reverse_lut, outf)

    print("done.")

