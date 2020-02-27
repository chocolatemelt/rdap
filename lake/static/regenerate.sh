cd $(dirname $0)
curl -O http://static.developer.riotgames.com/docs/lol/seasons.json
curl -O http://static.developer.riotgames.com/docs/lol/queues.json
curl -O https://ddragon.leagueoflegends.com/realms/na.json
curl -O https://ddragon.leagueoflegends.com/api/versions.json

# this thing is massive, uncomment at your own risk
# curl -O https://ddragon.leagueoflegends.com/cdn/dragontail-10.4.1.tgz \
# 	&& tar xf dragontail-10.4.1.tgz \
# 	&& rm -f dragontail-10.4.1.tgz
