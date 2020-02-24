import json
import requests
import sys
import urllib
import yaml

config = yaml.safe_load(open('config.yml'))

RGAPI_KEY = config['riot']['api_key']
RGAPI_REGION = config['riot']['region']

def get_route_to(route):
    return f'https://{RGAPI_REGION}.api.riotgames.com{route}'

def get_auth_headers():
    return {
        'Accept-Charset': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Riot-Token': RGAPI_KEY,
        'Accept-Language': 'en-US,en;q=0.5',
    }

def get_eaid(summoner_name):
    ROUTE = f'/lol/summoner/v4/summoners/by-name/{urllib.parse.quote(summoner_name)}'
    response = requests.get(get_route_to(ROUTE), headers=get_auth_headers())
    return response.json()['accountId']

def get_matchlist(eaid):
    ROUTE = f'/lol/match/v4/matchlists/by-account/{eaid}'
    response = requests.get(get_route_to(ROUTE), headers=get_auth_headers())
    return response.json()['matches']

if __name__ == '__main__':
    SUMMONER = sys.argv[1]
    if len(sys.argv) > 2:
        print('too many arguments! did you forget to wrap the name in quotes?')
        sys.exit(1)
    print(f'getting data for {SUMMONER}...')
    print(f'{SUMMONER}\'s encrypted account ID is {get_eaid(SUMMONER)}')
    print(json.dumps(get_matchlist(get_eaid(SUMMONER)), indent=2))

