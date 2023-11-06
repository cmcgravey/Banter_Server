import click
import threading
import socket
import json
import logging
import requests
import bs4
import time
from datetime import datetime, timedelta
from BNTRserver.questionBuilder import gameSession

# logger records output of server 
LOGGER = logging.getLogger(__name__)

class Server:

    def game_loop(self):
        """Search for games happening soon and insert into database to begin questions thread."""
        LOGGER.info("Inserting teams...")
        self.insert_teams()
        LOGGER.info("Inserting users...")
        self.insert_mock_users()

        next_game_found = False
        next = None
        next_time = None

        iterator = 0

        if self.DEBUG == True:
            self.insert_mock_games()
            self.insert_mock_users() 

        while self.signals['shutdown'] != True:

            current_time = datetime.now()

            if not next_game_found:
                LOGGER.info("Searching for games...")
                next, next_time = self.find_next_game()
                next_game_found = True

            diff = next_time - current_time
            if (iterator % 6 == 0):
                LOGGER.info(f'Game is {diff} away')

            if diff < timedelta(minutes=15):
                LOGGER.info("Starting gameSession... ")
                request_data = {
                    'api_key': self.API_KEY,
                    'status': "PREGAME",
                    'update': [0, 0, "00:00"]
                }
                requests.post(f'https://www.banter-api.com/api/games/{next["id"]}/', json=request_data)
                current_game = gameSession(next['id'], next['team1'], next['team2'])
                current_game.run_game_session()
                next_game_found = False
                if self.DEBUG == True:
                    self.DEBUG = False
            
            iterator += 1
            time.sleep(10)

    
    def insert_mock_users(self):
        """Insert eight mock users to database."""
        usernames = ['cmcgravey', 'samimud', 'ianglee', 'wraineri', 'jbergmann', 'cvenuti', 'dannyross', 'rwollaston']
        fullnames = ['Colin McGravey', 'Sami Muduroglu', 'Ian Lee', 'Will Raineri', 'Joe Bergmann', 'Chris Venuti', 'Danny Ross', 'Ryan Wollaston']
        scores = [42, 56, 24, 87, 36, 32, 65, 104]

        for i in range(0, 8):
            API_URL = 'https://www.banter-api.com/api/users/'
            user_json = {
                "api_key": self.API_KEY,
                "username": usernames[i],
                "password": 'password',
                "full_name": fullnames[i]
            }
            r = requests.post(API_URL, json=user_json)
            r = r.json()

            API_URL = f'https://www.banter-api.com/api/users/{r["userID"]}/'
            user_json = {
                "api_key": self.API_KEY,
                "type": "banter",
                "new_banter": scores[i]
            }
            r = requests.post(API_URL, json=user_json)
        

    def insert_mock_games(self):
        """Insert three mock games to database with different statuses."""
        status_list = ['PREGAME', 'IN_PLAY', 'HALFTIME']

        team_ids = [(9, 10), (4, 16), (11, 15)]
        updates = {
            "update0": [0, 0, "00:00"],
            "update1": [1, 0, "24:00"],
            "update2": [2, 1, "45:00"]
        }

        for i in range(0, 3):
            API_URL = 'https://www.banter-api.com/api/games/'
            ids = team_ids[i]

            game_json = {
                'api_key': self.API_KEY,
                'teamID1': ids[0],
                'teamID2': ids[1]
            }
            r = requests.post(API_URL, json=game_json)
            r = r.json()

            API_URL = f'https://www.banter-api.com/api/games/{r["id"]}/'
            update = updates[f'update{i}']

            game_update = {
                'api_key': self.API_KEY,
                'update': update,
                'status': status_list[i]
            }
            r = requests.post(API_URL, json=game_update)

    def find_next_game(self):
        """Find next upcoming game."""
        if self.DEBUG == True:
            next_game = ['', '', '', 'Burnley', '', '', '', 'Crystal Palace'] 
            game = self.insert_game(next_game)
            current_date = datetime.now()
            current_date += timedelta(minutes=15, seconds=40)
            game_string = current_date
            LOGGER.info(f'Gametime: {game_string}')
            LOGGER.info(f'Game: {game}')
            return game, game_string
        
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
                        LOGGER.info(f'Gametime: {game_string}')
                        LOGGER.info(f'Game: {game}')
                        break
        
        return game, game_string

    
    def insert_game(self, next_game):
        """Insert game into the database."""

        if self.DEBUG == True: 
            context = {
                'api_key': self.API_KEY,
                'teamID1': self.teams_dict['Burnley'],
                'teamID2': self.teams_dict['Crystal Palace']
            }

        else: 
            home = next_game[3].text
            away = next_game[7].text
            teamID1 = self.teams_dict[home]
            teamID2 = self.teams_dict[away]

            context = {
                'api_key': self.API_KEY,
                'teamID1': teamID1,
                'teamID2': teamID2
            }

        api_url = 'https://www.banter-api.com/api/games/'
            
        r = requests.post(api_url, json=context)
        response = r.json()

        return response

                
    def insert_teams(self):
        """Insert teams into the database."""

        url = 'https://fbref.com/en/comps/9/Premier-League-Stats'
        page = requests.get(url)

        soup = bs4.BeautifulSoup(page.text, 'html.parser')
        teams = soup.find_all('th', attrs={"class":"left"})

        for idx, item in enumerate(teams):
            if idx == 20:
                break

            name = item.text
            abbr = name[0] + name[1] + name[2]
            if abbr == 'Man':
                temp, second = name.split()
                if second == 'City':
                    abbr = 'MCI'
                else:
                    abbr = 'MUN'

            context = {
                "api_key": self.API_KEY,
                "name": item.text, 
                "abbr": abbr.upper(),
                "logo": f'{item.text}.png',
            }

            api_url = 'https://www.banter-api.com/api/teams/'
            
            r = requests.post(api_url, json=context)
            response = r.json()
            self.teams_dict[response['name']] = response['teamid']

        LOGGER.info(self.teams_dict)
   

    def __init__(self, host, port):
        """Initalize Server."""
        self.signals = {"shutdown": False}
        LOGGER.info("Starting Server...")

        ## INITIALIZE MEMBER VARIABLES HERE IF NEED BE 
        self.host = host
        self.port = port
        self.DEBUG = False

        ## INITIALIZE API KEY 
        self.API_KEY = '87ab0a3db51d297d3d1cf2d4dcdcb71b'
        self.teams_dict = {}

        self.game_thread = threading.Thread(target=self.game_loop)
        self.game_thread.start()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen()
            sock.settimeout(1)

            while True:
                # accept messages on given host and port
                try:
                    clientsocket, address = sock.accept()
                except socket.timeout:
                    continue
                clientsocket.settimeout(1)

                with clientsocket:
                    message_chunks = []
                    while True:
                        try:
                            data = clientsocket.recv(4096)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        message_chunks.append(data)

                message_bytes = b''.join(message_chunks)
                message_str = message_bytes.decode("utf-8")

                message_dict = {}

                try:
                    message_dict = json.loads(message_str)
                except json.JSONDecodeError:
                    message_dict = {"message_type": "error"}

                if message_dict["message_type"] == "error":
                    continue

                if message_dict["message_type"] == "shutdown":
                    LOGGER.info("shutdown received")
                    self.signals["shutdown"] = True
                    self.game_thread.join()
                    LOGGER.info("shutting down")
                    return


@click.command()
@click.option("--host", "host", default="localhost")
@click.option("--port", "port", default=6000)
@click.option("--logfile", "logfile", default=None)
@click.option("--loglevel", "loglevel", default="info")
def main(host, port, logfile, loglevel):
    """Run Server."""
    if logfile:
        handler = logging.FileHandler(logfile)
    else:
        handler = logging.StreamHandler()

    formatter = logging.Formatter(
        f"Updater:{port} %(message)s"
    )    
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(loglevel.upper())
    Server(host, port)

if __name__ == "__main__":
    main()