# Made by Bhaskar Balaji, Aug 2019
# Written primarily for use by the JHU A and B teams, as well as IBM's CEA team
# Free for anyone to use (pls credit me if relevant; I'm proud of this, simple though it is)

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("ids", nargs="+", help="summoner names to scout")
parser.add_argument(
    "-a", help="highlight champs shared with JHU A team", action="store_true"
)
parser.add_argument(
    "-b", help="highlight champs shared with JHU B team", action="store_true"
)
parser.add_argument(
    "-d",
    "--days",
    help="maximum number of days ago to count recent champs from",
    default="21",
)
parser.add_argument("--noflex", help="don't include flex games", action="store_true")
parser.add_argument("--norms", help="include normal games", action="store_true")

args = parser.parse_args()

shared_list = []
# For A team
if args.a:
    shared_list += [
        "Renekton",
        "Aatrox",
        "Sett",
        "Rek'Sai",
        "Zac",
        "Gragas",
        "Camille",
        "Syndra",
        "Yasuo",
        "Orianna",
        "Cassiopeia",
        "Galio",
        "Varus",
        "Ezreal",
        "Lucian",
        "Pyke",
        "Leona",
        "Nautilus",
        "Braum",
    ]
# shared_list = ['Renekton', 'Aatrox', 'Sett', 'Zac', "Rek'Sai", 'Gragas', 'Elise', 'Yasuo', 'Syndra', 'Kayn', 'Pyke'] # based on actual recent play

# For B team, based on preferences and recent picks
if args.b:
    shared_list += [
        "Ornn",
        "Kled",
        "Sett",
        "Poppy",
        "Ekko",
        "Jarvan IV",
        "Zac",
        "Rek'Sai",
        "Sejuani",
        "Nautilus",
        "Leona",
        "Braum",
        "Morgana",
        "Cassiopeia",
        "Ryze",
        "Syndra",
        "Corki",
        "Qiyana",
        "Aphelios",
        "Lucian",
        "Caitlyn",
        "Miss Fortune",
        "Braum",
        "Morgana",
        "Nautilus",
        "Nami",
        "Leona",
    ]

# Get parsed HTML from URL
def get_soup(url):
    return BeautifulSoup(requests.get(url).text, "html.parser")


flex = not args.noflex  # include flex?
recent_limit = args.days + "d"

ranked_only = not args.norms
max_entries = 30
num_to_lane = {0: "Top", 1: "Jungle", 2: "Mid", 3: "Bot", 4: "Support", 5: ""}
lane_to_num = {y: x for x, y in num_to_lane.items()}
# Get most recently played champs
def recent_games(user, soup):
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

            if user.lower() in summoners:
                data += [
                    {
                        "Champion": game.find(class_="ChampionName").a.string,
                        "Win": game["data-game-result"] == "win",
                        "Lane": num_to_lane[summoners.index(user.lower()) % 5],
                    }
                ]

            if len(data) >= max_entries:
                break

        if len(data) >= max_entries or late:
            break

        # Call another set of games
        page = requests.get(
            "https://na.op.gg/summoner/matches/ajax/averageAndList/startInfo="
            + game_time
            + "&summonerId="
            + summoner_id
        )
        if "json" in page.headers["Content-Type"]:
            soup = BeautifulSoup(page.json()["html"], "html.parser")
        else:
            soup = BeautifulSoup(page.text, "html.parser")

    if not data:
        return pd.DataFrame(columns=["Champion", "Games", "Wins"]), ""

    # Calculate games/wins (and lane preference) on the data
    df = pd.DataFrame(data)
    gp = df.groupby("Champion").agg(Games=("Champion", "count"), Wins=("Win", "sum"))
    gp = gp.sort_values("Games", ascending=False).astype({"Wins": int})

    lanes = list(df["Lane"].value_counts().index)
    return gp.reset_index(), lanes[0]


def season_stats(user, season_id):
    # Grab the HTML for the op.gg Champions page
    soup = get_soup("https://na.op.gg/summoner/champions/userName=" + user)
    soloq = soup.find(class_="tabItem " + season_id)

    if not soloq.find(class_="Body"):
        soloq_soup = get_soup("https://na.op.gg" + soloq["data-tab-data-url"])

        # In case someone has no soloq
        if not soloq_soup.tbody:
            return pd.DataFrame(columns=["Champion", "Games", "Winrate", "Pickrate"])

        # Each row has data on one champ
        rows = soloq_soup.tbody.find_all(class_="Row")
    else:
        rows = soloq.find(class_="Body").find_all(class_="Row")

    champ_data = []

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
    n = sum(df.Pickrate > 5)
    # Make sure 5 <= n <= 10
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


# Grab users from command line
c = "".join(args.ids)
if "," in c:
    # if C/Ped from op.gg (or names include spaces)
    users = c.split(",")
else:
    # if input as normal command-line args
    users = args.ids

if not users:
    print("No names supplied!")
    sys.exit()

# Lists of outputs
out_rec = []
out_s10 = []
out_s9 = []

lanes = []
ranks_s10 = []
ranks_prev = []

# For the purpose of calculating team average rank
ranksum = 0
rankn = 0
rankval = {"I": 0, "B": 1, "S": 2, "G": 3, "P": 4, "D": 5, "M": 6, "GM": 7, "C": 8}
valrank = {x: y for y, x in rankval.items()}

for user in users:
    print(user)

    # Find the user's soloq rank
    rank_soup = get_soup("https://na.op.gg/summoner/userName=" + user)

    # End program if name not found
    if rank_soup.find(class_="SummonerNotFoundLayout"):
        print("Summoner not found! Check spelling?")
        sys.exit()

    recent = recent_games(user, rank_soup)
    out_rec += [recent[0]]
    lanes += [recent[1]]

    ranks_s10 += [rank_soup.find(class_="TierRank").string.strip()]

    # Find the user's last recorded previous-season rank
    lastrank = rank_soup.find_all(class_="Item tip")
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

    out_s10 += [season_stats(user, "season-15")]
    out_s9 += [season_stats(user, "season-13")]

# Team avg rank (S9)
rankavg = ranksum / rankn
# If high elo (Master+)
if rankavg >= 6:
    teamrank = valrank[round(rankavg)]
    teamrankfine = ""
else:
    teamrank = valrank[int(rankavg)]
    teamrankfine = 4 - (int(4 * rankavg) - 4 * int(rankavg))

print(f"\nTeam's average S9 rank: {teamrank}{teamrankfine}")
print(f'https://na.op.gg/summoner/userName={",".join(users)}\n')

# Put queried players into standard role order
lane_nums = [lane_to_num[x] for x in lanes]
order = [y[1] for y in sorted([(x, i) for i, x in enumerate(lane_nums)])]


def reorder(l):
    return [l[i] for i in order]


users, out_rec, out_s10, out_s9, lanes, ranks_s10, ranks_prev = [
    reorder(x) for x in [users, out_rec, out_s10, out_s9, lanes, ranks_s10, ranks_prev]
]

# Determining spacing between rows [recent -- S10 -- S9]
rec_maxn = max([len(x.head(10)) for x in out_rec])
s10_maxn = max([len(x) for x in out_s10])

start_rec = 3
start_s10 = 3 + rec_maxn + 3
start_s9 = 3 + rec_maxn + 3 + s10_maxn + 3

# Find any shared champions
grp_champs = [x.Champion.tolist() for x in out_s10]
grp = [i for x in grp_champs for i in x]
sort_grp = sorted(
    [[x, grp.count(x)] for x in set(grp)], key=lambda x: x[1], reverse=True
)[1:]
print(
    "Champs played by multiple people in S10: "
    + ", ".join([x[0] for x in sort_grp if x[1] > 1])
    + "\n"
)

# Find top picks
tops = []
for rec, s10 in zip(out_rec, out_s10):
    tops += rec[rec.Games > 2].Champion.tolist()
    tops += s10[s10.Pickrate > 10].Champion.tolist()
tops = [x for i, x in enumerate(tops) if i != 0 and x not in tops[:i] and x != "Total"]
print("Priority champs: " + ", ".join(tops) + "\n")

# Styling functions
def shared(val):
    return "background-color: #f4cccc" if val in shared_list else ""


def rec_hi(val):
    return (
        "background-color: #00ff00"
        if val > 9
        else "background-color: #b7e1cd"
        if val > 4
        else ""
    )


def wr_hi(val):
    return (
        "background-color: #00ff00"
        if val > 70
        else "background-color: #b7e1cd"
        if val > 60
        else ""
    )


def pr_hi(val):
    return (
        "background-color: #00ff00"
        if val > 30
        else "background-color: #b7e1cd"
        if val > 15
        else ""
    )


# Output the data in order, horizontally, in 3 rows [recent -- S10 -- S9]
# out_file = "champ_data.xlsx"
# writer = pd.ExcelWriter(out_file)
# for i, (rec, s10, s9) in enumerate(zip(out_rec, out_s10, out_s9)):
#     rec.head(10).style.applymap(shared, "Champion").applymap(
#         rec_hi, ["Games", "Wins"]
#     ).to_excel(writer, index=False, startrow=start_rec, startcol=4 * i)
#     s10.style.applymap(shared, "Champion").applymap(wr_hi, "Winrate").applymap(
#         pr_hi, (range(len(s10) - 1), "Pickrate")
#     ).to_excel(writer, index=False, startrow=start_s10, startcol=4 * i)
#     s9.style.applymap(shared, "Champion").applymap(wr_hi, "Winrate").applymap(
#         pr_hi, (range(len(s9) - 1), "Pickrate")
#     ).to_excel(writer, index=False, startrow=start_s9, startcol=4 * i)
# writer.save()

# And label them by player name and rank (and adjust the column widths)
# book = openpyxl.load_workbook(out_file)
# sheet = book.active
# sheet.cell(1, 1).value = f'https://na.op.gg/summoner/userName={",".join(users)}'
# sheet.cell(
#     2, 1
# ).value = f'Champs played in the last {recent_limit} in {"ranked" + (" + flex" if flex else "") if ranked_only else ""} games'

# for i, user in enumerate(users):
#     sheet.cell(start_rec, 1 + 4 * i).value = user
#     sheet.cell(start_rec, 2 + 4 * i).value = lanes[i]

#     sheet.cell(start_s10, 1 + 4 * i).value = user
#     sheet.cell(start_s10, 2 + 4 * i).value = ranks_s10[i]
#     sheet.cell(start_s10, 3 + 4 * i).value = "S10"

#     sheet.cell(start_s9, 1 + 4 * i).value = user
#     sheet.cell(start_s9, 2 + 4 * i).value = ranks_prev[i]

#     sheet.column_dimensions[openpyxl.utils.get_column_letter(1 + 4 * i)].width = 12
#     sheet.column_dimensions[openpyxl.utils.get_column_letter(2 + 4 * i)].width = 12
# book.save(out_file)
