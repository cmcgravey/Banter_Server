import click
import threading
import socket
import json
import logging
import requests
import bs4


# logger records output of server 
LOGGER = logging.getLogger(__name__)

class Server:

    def game_loop(self):
        """Search for games happening soon and insert into database to begin questions thread."""
        self.insert_teams()
        

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

            api_url = 'http://ec2-34-238-139-153.compute-1.amazonaws.com/api/teams/'
            
            r = requests.post(api_url, json=context)
            response = r.json()
            self.teams_dict[response['teamid']] = response['name']

        LOGGER.info(self.teams_dict)
            

    def __init__(self, host, port):
        """Initalize Server."""
        self.signals = {"shutdown": False}
        LOGGER.info("Starting Server...")

        ## INITIALIZE MEMBER VARIABLES HERE IF NEED BE 
        self.host = host
        self.port = port

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