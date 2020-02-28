import argparse
from bs4 import BeautifulSoup
import pandas as pd
import requests
import rgutils
import sys
import urllib

LANE_MAPPING = {0: "Top", 1: "Jungle", 2: "Mid", 3: "Bot", 4: "Support", 5: ""}
OPGG_REGION = "na"


def opgg_season(season):
    return f"season-{season}"


def boil(url):
    return BeautifulSoup(requests.get(url).text, "lxml")


def get_opgg_route(route, params={}, region=OPGG_REGION):
    parsed_params = urllib.parse.urlencode(params)
    return f"https://{region}.op.gg{route}{parsed_params}"


def boil_opgg(route, params={}, region=OPGG_REGION):
    opgg_soup = boil(get_opgg_route(route, params, region))

    if opgg_soup.find(class_="SummonerNotFoundLayout"):
        raise ValueError("summoner not found")

    return opgg_soup


def recent_games(
    summoner, recent_limit="21d", flex=False, ranked_only=True, max_entries=30
):
    soup = boil_opgg("/summoner/", {"userName": summoner})
    data = []
    late = 0
    while not soup.find_all(string="There are no results recorded."):
        for x in soup.find_all(class_="GameItemWrap"):
            game = x.find(class_="GameItem")

            # Get timestamp of game (in KR timezone in op.gg -> Pacific)
            t = pd.Timestamp(
                str(game.find(class_="TimeStamp").span.string)
            ) - pd.Timedelta("17h")

            # Stop collecting games that are too old
            if pd.Timestamp.now() - t > pd.Timedelta(recent_limit):
                late = 1
                break

            game_time, summoner_id = game["data-game-time"], game["data-summoner-id"]

            # Search for 'Rank' to include flex; otherwise 'Solo'
            if ("Rank" if flex else "Solo") not in game.find(
                class_="GameType"
            ).string.strip() and ranked_only:
                continue
            if game.find(class_="GameResult").string.strip() == "Remake":
                continue

            summoners = [
                x.a.string.replace(" ", "").lower()
                for x in game.find_all(class_="SummonerName")
            ]

            if summoner in summoners:
                data += [
                    {
                        "Champion": game.find(class_="ChampionName").a.string,
                        "Win": game["data-game-result"] == "win",
                        "Lane": LANE_MAPPING[summoners.index(summoner) % 5],
                    }
                ]

            if len(data) >= max_entries:
                break

        if len(data) >= max_entries or late:
            break

        # Call another set of games
        page = requests.get(
            get_opgg_route(
                "/summoner/matches/ajax/averageAndList/",
                {"startInfo": game_time, "summonerId": summoner_id},
            )
        )
        if "json" in page.headers["Content-Type"]:
            soup = BeautifulSoup(page.json()["html"], "lxml")
        else:
            soup = BeautifulSoup(page.text, "lxml")

    if not data:
        return pd.DataFrame(columns=["Champion", "Games", "Wins"]), ""

    # Calculate games/wins (and lane preference) on the data
    df = pd.DataFrame(data)
    gp = df.groupby("Champion").agg(Games=("Champion", "count"), Wins=("Win", "sum"))
    gp = gp.sort_values("Games", ascending=False).astype({"Wins": int})

    lanes = list(df["Lane"].value_counts().index)
    return gp.reset_index(), lanes


def season_stats(summoner, season_id):
    soup = boil_opgg("/summoner/champions/", {"userName": summoner})
    soloq = soup.find(class_="tabItem " + season_id)
    rows = []
    champ_data = []

    if not soloq.find(class_="Body"):
        soloq_soup = boil_opgg(soloq["data-tab-data-url"])

        # In case someone has no soloq
        if not soloq_soup.tbody:
            return pd.DataFrame(columns=["Champion", "Games", "Winrate", "Pickrate"])

        rows = soloq_soup.tbody.find_all(class_="Row")
    else:
        rows = soloq.find(class_="Body").find_all(class_="Row")

    for row in rows:
        champ = row.find(class_="ChampionName")["data-value"]
        # The W/L are stored just as strings like 5W, 3L, ...
        results = row.find_all(class_="Text")
        # Usually there should be both wins and losses
        if len(results) == 2:
            wins = results[0].string.replace("W", "")
            losses = results[1].string.replace("L", "")
        # But if either W or L is 0, only the other exists
        else:
            if "W" in results[0].string:
                wins = results[0].string.replace("W", "")
                losses = 0
            else:
                wins = 0
                losses = results[0].string.replace("L", "")

        champ_data += [{"Champion": champ, "Wins": int(wins), "Losses": int(losses)}]

    df = pd.DataFrame(champ_data)
    df["Games"] = df.Wins + df.Losses
    df["Winrate"] = round(df.Wins / df.Games * 100, 1)
    df["Pickrate"] = round(df.Games / df.Games.sum() * 100, 1)

    # Retain all champs with pickrate >5% (could adjust to anything else)
    # and ake sure 5 <= n <= 10
    n = sum(df.Pickrate > 5)
    n = min(max(n, 5), 10)
    subset = df[["Champion", "Games", "Pickrate", "Winrate"]].head(n)

    return subset.append(
        {
            "Champion": "Total",
            "Games": subset.Games.sum(),
            "Pickrate": subset.Pickrate.sum(),
            "Winrate": (
                (subset.Winrate * subset.Games).sum() / subset.Games.sum()
            ).round(1),
        },
        ignore_index=True,
    )


def opgg_user(summoner):
    # Lists of outputs
    out_rec = []
    out_cur_season = []
    out_last_season = []

    lanes = []
    ranks_s10 = []
    ranks_prev = []

    # For the purpose of calculating team average rank
    ranksum = 0
    rankn = 0
    rankval = {"I": 0, "B": 1, "S": 2, "G": 3, "P": 4, "D": 5, "M": 6, "GM": 7, "C": 8}

    soup = boil_opgg("/summoner/", {"userName": summoner})

    recent = recent_games(summoner)
    out_rec += [recent[0]]
    lanes += [recent[1]]

    ranks_s10 += [soup.find(class_="TierRank").string.strip()]

    # Find the user's last recorded previous-season rank
    lastrank = soup.find_all(class_="Item tip")
    if lastrank:
        sn = lastrank[-1].b.string
        lastrank = lastrank[-1]["title"].split()
        # If it looks like 'Diamond 4 30LP'
        if len(lastrank) == 3:
            hielo = 0
            # Make it 'D4'
            lastrank = lastrank[0][0] + lastrank[1]
        else:
            hielo = 1
            # Include LP
            if "Grand" in lastrank[0]:
                lastrank = "GM " + lastrank[1]
            else:
                lastrank = lastrank[0][0] + " " + lastrank[1]
        ranks_prev += [sn + " " + lastrank]

        # Calculating the average rank (doesn't work great for high elo; 400LP is treated same as 0LP)
        # Currently this computes average rank only for S9 (can be changed once ranks settle in S10)
        if sn == "S9":
            rankn += 1
            if lastrank[1] == "M":
                ranksum += rankval["GM"]
            else:
                ranksum += rankval[lastrank[0]]
                if not hielo:
                    ranksum += (4 - float(lastrank[-1])) / 4
    else:
        ranks_prev += ["no prev. rank"]

    out_cur_season += [season_stats(summoner, opgg_season(rgutils.get_season()))]
    out_last_season += [season_stats(summoner, opgg_season(rgutils.get_last_season()))]

    print(out_rec, out_cur_season, out_last_season)


if __name__ == "__main__":
    user = "go in idiot".replace(" ", "").lower()
    opgg_user(user)

