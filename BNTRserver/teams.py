"""Class to handle teams insertion."""
import json
import logging
import requests


LOGGER = logging.getLogger(__name__)

class TeamsHandler():

    def __init__(self, league, banter_key):
        """Create class instance."""
        self.LEAGUE = league
        self.TEAMS_DICT = {}
        self.BANTER_API_KEY = banter_key

        self.SPORTS_API_HEADERS = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

        self.MLS_QUERY = {
            "league": 253,
            "season": 2023,
        }

        self.PREM_QUERY = {
            "league": 39,
            "season": 2023,
        }

        self.insert_teams()

    def fetch_teams_dict(self):
        return self.TEAMS_DICT

    def send_to_db(self, teams_list):
        """Send list of teams to Database."""
        api_url = 'https://www.banter-api.com/api/teams/'

        for team in teams_list:
            r = requests.post(api_url, json=team)
            response = r.json()
            self.TEAMS_DICT[response['name']] = response['teamid']

    def insert_teams(self):
        """Insert teams from MLS into the database."""
        url = "https://api-football-v1.p.rapidapi.com/v3/teams"
        team_list = []
        if self.LEAGUE == 'MLS':
            r = requests.get(url, headers=self.SPORTS_API_HEADERS, params=self.MLS_QUERY)
            data = r.json()
        elif self.LEAGUE == 'PREMIER':
            r = requests.get(url, headers=self.SPORTS_API_HEADERS, params=self.PREM_QUERY)
            data = r.json()
        
        for team in data["response"]:
            if team['team']['code'] == None:
                abbr = 'NON'
            else:
                abbr = team['team']['code']
            context = {
                "api_key": self.BANTER_API_KEY,
                "name": team['team']['name'],
                "abbr": abbr,
                "logo": team['team']['logo']
            }
            team_list.append(context)
        
        self.send_to_db(team_list)
