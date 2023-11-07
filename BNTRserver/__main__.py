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
from BNTRserver.teams import TeamsHandler
from BNTRserver.games import GameHandler

# logger records output of server 
LOGGER = logging.getLogger(__name__)

class Server:

    def game_loop(self, league):
        """Search for games happening soon and insert into database to begin questions thread."""

        ## Insert teams into database and retrieve dictionary 
        LOGGER.info(f'Inserting {league} teams... ')
        t = TeamsHandler(league, self.API_KEY)
        self.teams_dict = t.fetch_teams_dict()
        LOGGER.info(self.teams_dict)

        ## Insert mock games to database
        if self.DEBUG == True:
            self.insert_mock_games()

        ## Setup game loop 
        next_game_found = False
        next = None
        next_time = None
        iterator = 0
        g = GameHandler(league, self.API_KEY, self.DEBUG, self.teams_dict)

        ## Begin game loop
        while self.signals['shutdown'] != True:

            ## Find next game
            if not next_game_found:
                LOGGER.info(f'Searching for {league} games...')
                next, next_time = g.game_handler()
                next_game_found = True

            ## Find difference between curr time and start time
            current_time = datetime.now()
            diff = next_time - current_time
            if (iterator % 6 == 0):
                LOGGER.info(f'{league} Game is {diff} away')

            ## If game is within 15 minutes of starting, update status and begin gameSession
            if diff < timedelta(minutes=15):
                LOGGER.info(f'Starting {league} gameSession... ')
                request_data = {
                    'api_key': self.API_KEY,
                    'status': "PREGAME",
                    'update': [0, 0, "00:00"]
                }
                requests.post(f'https://www.banter-api.com/api/games/{next["id"]}/', json=request_data)
                ## current_game = gameSession(next['id'], next['team1'], next['team2'])
                ## current_game.run_game_session()
                ## next_game_found = False
                if self.DEBUG == True:
                    self.DEBUG = False
            
            ## Increment iterator and sleep
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
   
    def __init__(self, host, port):
        """Initalize Server."""
        self.signals = {"shutdown": False}
        LOGGER.info("Starting Server...")

        ## INITIALIZE MEMBER VARIABLES HERE IF NEED BE 
        self.host = host
        self.port = port
        self.DEBUG = False
        self.THREADS = []

        ## INITIALIZE API KEY 
        self.API_KEY = '87ab0a3db51d297d3d1cf2d4dcdcb71b'
        self.teams_dict = {}

        ## Insert mock users to database
        LOGGER.info("Inserting users...")
        self.insert_mock_users() 

        ## Premier League Game thread
        LOGGER.info("Starting Premier League thread...")
        game_thread_prem = threading.Thread(target=self.game_loop, args=['PREMIER'])
        game_thread_prem.start()
        self.THREADS.append(game_thread_prem)

        ## MLS Game thread
        LOGGER.info("Starting MLS thread...")
        game_thread_mls = threading.Thread(target=self.game_loop, args=['MLS'])
        game_thread_mls.start()
        self.THREADS.append(game_thread_mls)

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
                    for thread in self.THREADS:
                        thread.join()
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