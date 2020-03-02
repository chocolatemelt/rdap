import json
import os

if __name__ == "__main__":
    here = os.path.dirname(__file__)
    reverse = []

    print("reversing...")
    with open(os.path.join(here, "seasons.json"), "r") as inf:
        seasons = json.load(inf)
        for s in seasons:
            reverse.insert(0, s)

    with open(os.path.join(here, "seasons.json"), "w") as outf:
        json.dump(reverse, outf)

    print("done.")
