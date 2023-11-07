"""Class to handle teams insertion."""
import json
import logging
import requests
import bs4


LOGGER = logging.getLogger(__name__)

class TeamsHandler():

    def __init__(self, league, key):
        """Create class instance."""
        self.LEAGUE = league
        self.TEAMS_DICT = {}
        self.API_KEY = key
        self.teams_handler()

    def fetch_teams_dict(self):
        return self.TEAMS_DICT

    def send_to_db(self, teams_list):
        """Send list of teams to Database."""
        api_url = 'https://www.banter-api.com/api/teams/'

        for team in teams_list:
            r = requests.post(api_url, json=team)
            response = r.json()
            self.TEAMS_DICT[response['name']] = response['teamid']

    def teams_handler(self):
        """Handle traffic into different league functions."""
        teams_list = []
        if self.LEAGUE == 'MLS':
            teams_list = self.insert_teams_mls()
        elif self.LEAGUE == 'PREMIER':
            teams_list = self.insert_teams_prem()

        self.send_to_db(teams_list)

    def insert_teams_mls(self):
        """Insert teams from MLS into the database."""
        url = 'https://fbref.com/en/comps/22/Major-League-Soccer-Stats'
        team_list = []

        try:
            page = requests.get(url)

            if page.status_code == 200:
                soup = bs4.BeautifulSoup(page.text, 'html.parser')
                teams = soup.find_all('th', attrs={"class":"left"})

                if teams: 
                    for idx, team in enumerate(teams):
                        if idx == 29:
                            break
                        name = team.text
                        name = name.strip()
                        abbr = name[0] + name[1] + name[2]
                        context = {
                            "api_key": self.API_KEY,
                            "name": name, 
                            "abbr": abbr.upper(),
                            "logo": f'{name}.png'
                        }
                        team_list.append(context)
                    
            else:
                LOGGER.info(f"Failed to retrieve the webpage, Status Code: {page.status_code}")
        except Exception as e:
            LOGGER.info(f"Error occured: {str(e)}")

        return team_list
    
    def insert_teams_prem(self):
        """Insert teams from Premier League into the database."""
        url = 'https://fbref.com/en/comps/9/Premier-League-Stats'
        team_list = []

        try: 
            page = requests.get(url)

            if page.status_code == 200:

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

                    team_list.append(context)
            else:
                LOGGER.info(f"Failed to retrieve the webpage, Status Code: {page.status_code}")
        except Exception as e:
            LOGGER.info(f"Error occured: {str(e)}")

        return team_list
