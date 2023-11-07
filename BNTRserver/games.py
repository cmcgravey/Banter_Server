"""Class to handle game insertion."""
import json
import logging
import requests
import bs4
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)

MLS_TIMEZONES = {
    "Allianz Field": 1,
    "America First Field": 2,
    "Audi Field": 0,
    "Bank of America Stadium": 0, 
    "BC Place Stadium": 3,
    "BMO Field": 0, 
    "BMO Stadium": 3, 
    "Children's Mercy Park": 1,
    "Citi Field": 0, 
    "Citypark": 1,
    "Dick's Sporting Goods Park": 2,
    "Dignity Health Sports Park": 2,
    "DRV PNK Stadium": 0,
    "Exploria Stadium": 0,
    "Geodis Park": 1, 
    "Gillette Stadium": 0, 
    "Levi's Stadium": 3,
    "Lower.com Field": 0,
    "Lumen Field": 3,
    "Mercedes-Benz Stadium": 0,
    "PayPal Park": 3,
    "Providence Park": 3,
    "Q2 Stadium": 1,
    "Red Bull Arena": 0,
    "Rose Bowl": 3,
    "Shell Energy Stadium": 1,
    "Soldier Field": 1,
    "Stade Olympique": 0,
    "Stade Saputo": 0,
    "Stanford Stadium": 3,
    "Subaru Park": 0,
    "Toyota Stadium": 1,
    "TQL Stadium": 0,
    "Yankee Stadium": 0
}

class GameHandler():

    def __init__(self, league, api_key, debug, teams):
        """Create instance of game handler class."""
        self.LEAGUE = league
        self.API_KEY = api_key
        self.DEBUG = debug
        self.TEAMS_DICT = teams

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
            if self.LEAGUE == 'MLS':
                game, game_string = self.fetch_next_game_mls()
            elif self.LEAGUE == 'PREMIER':
                game, game_string = self.fetch_next_game_prem()
        else:
            game, game_string = self.debug_insert()
        
        LOGGER.info(f'{self.LEAGUE} Gametime: {game_string}')
        LOGGER.info(f'{self.LEAGUE} Game: {game}')

        return game, game_string

    def fetch_next_game_mls(self):
        """Find nearest upcoming game in MLS."""
        url = 'https://fbref.com/en/comps/22/schedule/Major-League-Soccer-Scores-and-Fixtures'
        page = requests.get(url)
        soup = bs4.BeautifulSoup(page.text, 'html.parser')

        fixture_table = soup.find('table', {'class': 'stats_table'})
        rows = fixture_table.find_all('tr')

        current_date = datetime.now()
        next_game = None

        for idx, row in enumerate(rows):
            cells = row.find_all('td')

            if cells == []:
                pass
            else:
                game_date = cells[1].text.replace('-', '/')
                game_time = cells[2].text.strip()
                game_time += ':00'
                game_string = game_date + ' ' + game_time
                game_string = datetime.strptime(game_string, '%Y/%m/%d %H:%M:%S')
                game_string = game_string + timedelta(hours=MLS_TIMEZONES[cells[9].text])
                if game_string >= current_date:
                    next_game = cells
                    game = self.insert_game(next_game)
                    break

            game = []
            game_string = ''

    
        return game, game_string
            
    def fetch_next_game_prem(self):
        """Find nearest upcoming game in Premier League."""
        url = 'https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures'
        page = requests.get(url)
        soup = bs4.BeautifulSoup(page.text, 'html.parser')

        fixture_table = soup.find('table', {'class': 'stats_table'})
        rows = fixture_table.find_all('tr')

        current_date = datetime.now()
        next_game = None

        for idx, row in enumerate(rows):
            if idx == 0:
                pass
            else:
                cells = row.find_all('td')
                if cells[1].text == '' or cells[2].text == '':
                    pass
                else:
                    game_date = cells[1].text.replace('-', '/')
                    game_time = cells[2].text.strip()
                    game_time += ':00'
                    game_string = game_date + ' ' + game_time
                    game_string = datetime.strptime(game_string, '%Y/%m/%d %H:%M:%S')
                    game_string = game_string - timedelta(hours=5)
                    if game_string >= current_date:
                        next_game = cells
                        game = self.insert_game(next_game)
                        break
        
        return game, game_string
    
    def insert_game(self, next_game):
        """Insert game into the database."""

        if self.DEBUG == True: 
            context = {
                'api_key': self.API_KEY,
                'teamID1': self.TEAMS_DICT['Chelsea'],
                'teamID2': self.TEAMS_DICT['Tottenham'],
                'league': self.LEAGUE
            }

        else: 
            home = next_game[3].text
            away = next_game[7].text
            teamID1 = self.TEAMS_DICT[home]
            teamID2 = self.TEAMS_DICT[away]

            context = {
                'api_key': self.API_KEY,
                'teamID1': teamID1,
                'teamID2': teamID2,
                'league': self.LEAGUE
            }

        api_url = 'https://www.banter-api.com/api/games/'
            
        r = requests.post(api_url, json=context)
        response = r.json()

        return response