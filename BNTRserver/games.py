"""Class to handle game insertion."""
import json
import logging
import requests
import time
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)

STATUS_DICT = {
    "SUSP": "Suspended",
    "PST": "Postponed",
    "CANC": "Cancelled",
    "ABD": "Abandoned",
    "AWD": "Technical Loss",
    "WO": "Forfeit"
}

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

    def fetch_next_game(self):
        """Find nearest upcoming game in MLS."""
        if self.LEAGUE == 'MLS':
            fixtures = self.call_sportsbook_api(self.MLS_QUERY)
        elif self.LEAGUE == 'PREMIER': 
            fixtures = self.call_sportsbook_api(self.PREM_QUERY)

        if fixtures == None:
            return None, None

        for fixture in fixtures:
            if fixture["fixture"]["status"]["short"] == "NS":
                context = {
                    "api_key": self.BANTER_API_KEY,
                    "teamID1": self.TEAMS_DICT[fixture["teams"]["home"]["name"]],
                    "teamID2": self.TEAMS_DICT[fixture["teams"]["away"]["name"]],
                    "league": self.LEAGUE,
                    "fixtureID": fixture["fixture"]["id"]
                }
                isoform = fixture["fixture"]["date"]
                game_string = datetime.fromisoformat(isoform)
                game_string_est = game_string - timedelta(hours=5)
                ds = game_string_est.strftime("%m/%d/%y - %I:%M %p")
                context["game_string"] = ds
                game = self.insert_game(context)
                break

        LOGGER.info(f'{self.LEAGUE} Gametime: {game_string}')
        LOGGER.info(f'{self.LEAGUE} Game: {game}')
        
        return game, game_string
    
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
        fixture_id = self.CURR_GAME['fixtureID']

        query = {
            'id': fixture_id
        }

        fixture = self.call_sportsbook_api(query=query)

        if fixture == None:
            return None
        elif fixture[0]["fixture"]["status"]["short"] in STATUS_DICT:
            LOGGER.info(f"Start Time update failed in {self.LEAGUE} thread: Game Status {STATUS_DICT[fixture[0]['fixture']['status']['short']]}")
            return None

        game_string = fixture[0]["fixture"]["date"]
        game_string = datetime.fromisoformat(game_string)
        
        return game_string
    
    def call_sportsbook_api(self, query, max_attempts=5, delay=5):
        """Call Sportsbook API."""
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(url, headers=self.SPORTS_API_HEADERS, params=query)
                data = response.json()
                fixtures = data['response']
                return fixtures
            except (KeyError, IndexError):
                if attempt < max_attempts - 1:
                    time.sleep(delay)
                else:
                    LOGGER.info("Sports API failed: games.py --> call_sportsbook_api()")
                    return None
