"""Class to handle game insertion."""
import json
import logging
import requests
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)

class GameHandler():

    def __init__(self, league, api_key, debug, teams):
        """Create instance of game handler class."""
        self.LEAGUE = league
        self.BANTER_API_KEY = api_key
        self.DEBUG = debug
        self.TEAMS_DICT = teams
        self.SPORTS_API_HEADERS = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"    
        }
        self.MLS_QUERY = {
            "league": 253,
            "season": 2023,
            "timezone": 'America/Detroit'
        }
        self.PREM_QUERY = {
            "league": 39,
            "season": 2023,
            "timezone": 'America/Detroit'
        }
        self.CURR_GAME = None

    def debug_insert(self):
        """Controlled insertion of game."""
        if self.DEBUG == True:
            next_game = []
            game = self.insert_game(next_game)
            current_date = datetime.now()
            current_date += timedelta(minutes=15, seconds=30)
            game_string = current_date
            LOGGER.info(f'{self.LEAGUE} Gametime: {game_string}')
            LOGGER.info(f'{self.LEAGUE} Game: {game}')
            return game, game_string
            
    def game_handler(self):
        game = None
        game_string = None

        if self.DEBUG is not True:
            game, game_string = self.fetch_next_game()
        else:
            game, game_string = self.debug_insert()
        
        LOGGER.info(f'{self.LEAGUE} Gametime: {game_string}')
        LOGGER.info(f'{self.LEAGUE} Game: {game}')

        return game, game_string

    def fetch_next_game(self):
        """Find nearest upcoming game in MLS."""
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

        if self.LEAGUE == 'MLS':
            response = requests.get(url, headers=self.SPORTS_API_HEADERS, params=self.MLS_QUERY)
            data = response.json()
        elif self.LEAGUE == 'PREMIER': 
            response = requests.get(url, headers=self.SPORTS_API_HEADERS, params=self.PREM_QUERY)
            data = response.json()

        for fixture in data["response"]:
            if fixture["fixture"]["status"]["short"] == "NS":
                context = {
                    "api_key": self.BANTER_API_KEY,
                    "teamID1": self.TEAMS_DICT[fixture["teams"]["home"]["name"]],
                    "teamID2": self.TEAMS_DICT[fixture["teams"]["away"]["name"]],
                    "league": self.LEAGUE,
                    "fixtureID": fixture["fixture"]["id"]
                }
                game_string = fixture["fixture"]["date"]
                game_string = datetime.fromisoformat(game_string)
                banter_rsp = self.insert_game(context)
                break
        
        return banter_rsp, game_string
    
    def insert_game(self, next_game):
        """Insert game into the database."""
        if self.DEBUG == True: 
            next_game = {
                'api_key': self.API_KEY,
                'teamID1': self.TEAMS_DICT['Chelsea'],
                'teamID2': self.TEAMS_DICT['Tottenham'],
                'league': self.LEAGUE,
                'fixtureID': 2
            }

        api_url = 'https://www.banter-api.com/api/games/'
            
        r = requests.post(api_url, json=next_game)
        response = r.json()
        self.CURR_GAME = response

        return response
    
    def check_game_start_time(self):
        """Check start time of the game."""
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        fixture_id = self.CURR_GAME['fixtureID']

        query = {
            'id': fixture_id
        }

        response = requests.get(url, headers=self.SPORTS_API_HEADERS, params=query)
        fixture = response.json()

        game_string = fixture["response"][0]["fixture"]["date"]
        game_string = datetime.fromisoformat(game_string)
        
        return game_string