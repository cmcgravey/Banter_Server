"""In-game Session Backend."""
import requests
import json
import random
import time
import logging

LOGGER = logging.getLogger(__name__)

class gameSession:
    def __init__(self, gameID, team1_id, team2_id):
        """In-Game Thread. Check game times and send filled-out questions to database periodically."""
        self.game_status = "IN PLAY"
        self.game_time = None
        self.game_stage = None
        
        # FOR TEST: Crystal Palace vs. Burnley
        # Event Id = f77d9e4a963ee0e68fb0f71d51fa6855
        self.DEBUG = True
        self.DEBUG_HT = True
        self.debug_index = 1
        
        self.gameID = gameID
        
        self.fixture_id = None
        self.prem_league_id = 39
        
        self.BANTER_API_KEY = "87ab0a3db51d297d3d1cf2d4dcdcb71b"
        self.BANTER_API_ENDPOINT = "http://ec2-34-238-139-153.compute-1.amazonaws.com/api/"
        
        team1_url = f"{self.BANTER_API_ENDPOINT}teams/{team1_id}/"
        team2_url = f"{self.BANTER_API_ENDPOINT}teams/{team2_id}"
        
        team1_response = requests.get(url=team1_url,json={"api_key": self.BANTER_API_KEY}).json()
        team2_response = requests.get(url=team2_url,json={"api_key": self.BANTER_API_KEY}).json()
        
        LOGGER.info("Sanity check")
        
        self.team1 = team1_response["name"]
        
        
        self.team2 = team2_response["name"]
        LOGGER.info(f"{self.team1}")
        LOGGER.info(f"{self.team2}")
        
        self.event_id = self.get_event_id(team1_response["name"], team2_response["name"])
        
        self.team1_goals = {
            "halftime": 0,
            "final": 0,
            "name": self.team1
            
        }
        
        self.team2_goals = {
            "halftime": 0,
            "final": 0,
            "name": self.team2
        }
        
        
        self.non_book_questions = ["next_goal", "yellow_cards", "red_card"]
        # Add in: Answer Options, gain/loss for answer
        self.question_templates = {}
        self.question_templates["pregame"] = [
            {"question_stage": "pregame",
             "label": "spreads",
             "question": "Predict the Spread",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "h2h",
             "question": "Who's going to win?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "totals",
             "question": "How many goals will be scored?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "yellow_cards",
             "question": "Will there be over 5 yellow cards played?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "btts",
             "question": "Will both teams score?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "red_card",
             "question": "Will there be a red card this game?",
             "Game_id": self.gameID}
        ]
        
        self.question_templates["ingame"] = [
            
            {"question_stage": "ingame",
             "label": "h2h_h1",
             "question": "Who's going to win this half?",
             "Game_id": self.gameID},
            
            {"question_stage": "ingame",
             "label": "totals_h1",
             "question": "How many goals will there be at the end of the half?",
             "Game_id": self.gameID},
            
        ]
        
        self.question_templates["halftime"] = [
            {"question_stage": "halftime",
             "label": "h2h_h2",
             "question": "Who's winning this half?",
             "Game_id": self.gameID},
            
            {"question_stage": "halftime",
             "label": "spreads_h2",
             "question": "Second half spread?",
             "Game_id": self.gameID},
            
            {"question_stage": "halftime",
             "label": "totals_h2",
             "question": "How many goals will there be in the second half?",
             "Game_id": self.gameID}
        ]
        
        self.run_game_session()
    def run_game_session(self):
        """Main thread for running the game"""
        self.build_questions("pregame")
        LOGGER.info("Creating pregame questions")
        self.locate_fixture_id()
        
        
        ingame_flag = False
        halftime_flag = False
        while self.game_status == "IN PLAY":
            # Check for game time
            self.track_game_time()
            if 20 <= self.game_time <= 30 and self.game_stage == "1H" and ingame_flag == False:
                ingame_flag = True
                self.build_questions("ingame")
                LOGGER.info("Creating ingame questions")
                
            elif self.game_stage == "HT" and halftime_flag == False:
                self.build_questions("halftime")
                LOGGER.info("Creating halftime questions")
                self.update_scores("halftime")
                halftime_flag = True
            time.sleep(60)
        self.update_scores("final")
        self.resolve_questions()
        LOGGER.info("Resolving question answers")
        return
    
    def update_scores(self, stage):
        """Keep data for the score at halftime for reference for answering questions."""
        scores = self.get_game_scores()
        for score in scores[0]["scores"]:
            if score["name"] == self.team1:
                self.team1_goals[stage] = int(score["score"])
            else:
                self.team2_goals[stage] = int(score["score"])
    
    def build_questions(self, question_stage):
        """Build questions based off of sports odds."""
        sportsbook_data = []
        staged_questions = random.sample(self.question_templates[question_stage], 1)
        markets = [question["label"] for question in staged_questions] 
        
        # Remove non-sportsbook related questions 
        for market in self.non_book_questions:
            if market in markets:
                markets.remove(market)   
        # Call sportsbook API to get data
        if len(markets) > 0:
            sportsbook_data = self.callSportsbookAPI(markets)
        # Build each question sequentially
        for i in range(len(staged_questions)):
            # Do different calculation for red and yellow cards, not based on sportsbook odds
            if staged_questions[i]["label"] == "yellow_cards" or staged_questions[i]["label"] == "red_card":
                # (Question text, points gained if correct, points lost if wrong)
                rewards, pens = self.calculate_banter_points([-100, 100])
                staged_questions[i]["opt1"] = ("Yes", rewards[0], pens[0])
                staged_questions[i]["opt2"] = ("No", rewards[1], pens[1])
            else:
                question_odds = self.find_market(sportsbook_data["bookmakers"], staged_questions[i])
                
                rewards, pens = self.calculate_banter_points([odds["price"] for odds in question_odds])

                for j in range(len(rewards)):
                    # These question labels don't require points in the question text
                    if staged_questions[i]["label"].startswith("h2h") or staged_questions[i]["label"] == "btts":
                        staged_questions[i][f"opt{j + 1}"] = (f"{question_odds[j]['name']}",rewards[j], pens[j])
                    # Totals and spread require the points in the question text
                    else:
                        staged_questions[i][f"opt{j + 1}"] = (f"{question_odds[j]['name']} {question_odds[j]['point']}",
                                                            rewards[j], pens[j])
            self.add_question(staged_questions[i])      
    
    def calculate_banter_points(self, lines):
        """Calculate banter points earned/lost based on converting US Moneyline to probability."""
        probs = []
        for line in lines:
            if line < 0:
                probs.append((-line) / (-line + 100))
            else:
                probs.append(100 / (line + 100))
        total_prob = sum(probs)
        question_probs = [p / total_prob for p in probs]
        rewards = [int(10 + 40 * p) for p in question_probs]
        penalties = [int(0.4 * r) for r in rewards]
        return rewards, penalties
                               
    def find_market(self, bookmakers, question):
        """Find a bookmaker that has the specific market question we are asking."""
        for bookmaker in bookmakers:
            for market in bookmaker["markets"]:
                if market.get("key") == question["label"]:
                    return market["outcomes"]
        
    def get_event_id(self, team1, team2):
        """Get event ID from game ID (From the Odds API), in order to fetch unique sports Odds."""
        # Use GET request to get team names using self.gameID
        SPORT = 'soccer_epl'
        
        API_KEY = '4176fcde0a060dfeb152fc085e8ec6f9'
        
        ENDPOINT = f'https://api.the-odds-api.com/v4/sports/{SPORT}/events/'
        if self.DEBUG == True:
            with open("testing/find_event_id.json", 'r') as file:
                odds_response = json.load(file)
        else:
            odds_response = requests.get(
                ENDPOINT,
                params={
                    'api_key': API_KEY,
                }
            )
        for event in odds_response:
            if team1 in event.values() and team2 in event.values():
                self.event_id = event["id"]
                return
    
    def callSportsbookAPI(self, markets):
        """Call sportsbook API to get odds."""
        API_KEY = '4176fcde0a060dfeb152fc085e8ec6f9'

        SPORT = 'soccer_epl' 

        REGIONS = 'uk,us' # uk | us | eu | au. Multiple can be specified if comma delimited

        MARKETS = ','.join(markets)

        ODDS_FORMAT = 'american' # decimal | american

        DATE_FORMAT = 'iso' # iso | unix

        # Event ID comes from get_event_id(), where we call sportsbook API and locate the correct event ID
        # Event ID is necessary in order to get more specific and special market odds
        EVENT_ID = self.event_id # Example: "5528d0b167ff7ae068b6d0478eb997c7" # Tottenham vs. Luton

        ENDPOINT = f'https://api.the-odds-api.com/v4/sports/{SPORT}/events/{EVENT_ID}/odds'
        
        if self.DEBUG == True:
            with open("testing/sportsbookOdds.json", 'r') as file:
                odds_response = json.load(file)
                return odds_response
        else:
            odds_response = requests.get(
                ENDPOINT,
                params={
                    'api_key': API_KEY,
                    'regions': REGIONS,
                    'markets': MARKETS,
                    'oddsFormat': ODDS_FORMAT,
                    'dateFormat': DATE_FORMAT,
                }
            )
            if odds_response.status_code == 200:
                print("Sportsbook API request successful")
                return json.loads(odds_response.text)
            else:
                print('SB API Request failed with status code:', odds_response.status_code)
                return {}
    
    def get_game_scores(self):
        """Use The-Odds API to get in-game scores"""
        API_KEY = '4176fcde0a060dfeb152fc085e8ec6f9'

        SPORT = 'soccer_epl' 
        
        EVENT_ID = self.event_id
        
        ENDPOINT = f"https://api.the-odds-api.com/v4/sports/{SPORT}/scores"
        
        if self.DEBUG == True:
            if self.DEBUG_HT == True:
                filename = "testing/get_scores_halftime.json"
                self.DEBUG_HT = False
            else:
                filename = "testing/get_scores_final.json"
            with open(filename, 'r') as file:
                odds_response = json.load(file)
                return odds_response
            
        else:
            odds_response = requests.get(
                ENDPOINT,
                params={
                    'api_key': API_KEY,
                    'daysFrom': 1,
                    'eventIds': EVENT_ID,
                }
            )
            if odds_response.status_code == 200:
                print("Sportsbook API request successful")
                return json.loads(odds_response.text)
            else:
                print('SB API Request failed with status code:', odds_response.status_code)
                return {}
            
        

        
    def add_question(self, question):
        """Once Questions are built, insert them back into database using banter API."""

        question["api_key"] = self.BANTER_API_KEY
        
        question_url = f"{self.BANTER_API_ENDPOINT}questions/{self.gameID}/"

        response = requests.post(url=question_url,json=question)
        
        if response.status_code == 200:
            print("POST Request | Question -> Database | Successful")
        else:
            print('Request failed with status code:', response.status_code)
        
        
    def track_game_time(self):
        """Use Rapid API for current game time. Called every minute."""
            
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures?live=all"
        
        # FOR TEST: Fixture Id: 1132545
        
        query = {"fixture": f"{self.fixture_id}"}
        
        headers = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        if self.DEBUG == True:
            with open(f"testing/track_game_time_{self.debug_index}.json", 'r') as file:
                data = json.load(file)
        else:
            response = requests.get(url, headers=headers, params=query)
            data = response.json()
        
        self.game_time = data["response"][0]["fixture"]["status"]["elapsed"]
        self.game_stage = data["response"][0]["fixture"]["status"]["short"]
        self.game_status = "Finished" if data["response"][0]["status"]["long"] == "Match Finished" else "IN PLAY"
        
        return
    
    def locate_fixture_id(self):
        """Locate the fixture ID for the Rapids API - Football API."""
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures?live=all"

        headers = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        
        query = {"league": str(self.prem_league_id)}
        
        if self.DEBUG == True:
            with open(f"testing/locate_fixture_id.json", 'r') as file:
                data = json.load(file)
        else:
            response = requests.get(url, headers=headers, params=query)
            data = response.json()

        for response in data["response"]:
            home = response["teams"]["home"].values()
            away = response["teams"]["away"].values()
            if (self.team1 in home or self.team2 in home) and (self.team1 in away or self.team2 in away):
                self.fixture_id = response["fixture"]["id"]
                return

    def resolve_questions(self):
        """Pull the questions from the database with a specific gameID, then resolve the answer for each one using Rapid API."""
        
        # Fetch all questions from database
        
        api_url = f"{self.BANTER_API_ENDPOINT}questions/{self.gameID}/"
        
        data = {"api_key": self.BANTER_API_KEY}
        
        response = requests.get(url=api_url, json=data)
        
        question_list = response.json()["questions"]
        
        # Fetching game statistics now from Rapid API
        
        stat_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"
        
        querystring = {"fixture": f"{self.fixture_id}"}
        
        headers = {
                "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        if self.DEBUG == True:
            with open(f"testing/postgame_statistics.json", 'r') as file:
                statistics = json.load(file)
        else:
            response = requests.get(stat_url, headers=headers, params=querystring)
            
            statistics = response.json()["response"]
        
        # Use questions and statistics to find answers and input back into database.
        
        if self.team1_goals["final"] == self.team2_goals["final"]:
            winning_team = "Draw"
        else:
            winning_team = max(self.team1_goals, self.team2_goals, key=lambda team: team["final"])["name"]
        
        if self.team1_goals["halftime"] == self.team2_goals["halftime"]:
            h1_winner = "Draw"
        else:
            h1_winner = max(self.team1_goals, self.team2_goals, key=lambda team: team["halftime"])["name"]
        
        if (self.team1_goals["final"] - self.team1_goals["halftime"]) > (self.team2_goals["final"] - self.team2_goals["halftime"]):
            h2_winner = self.team1_goals["name"]
            
        elif (self.team1_goals["final"] - self.team1_goals["halftime"]) < (self.team2_goals["final"] - self.team2_goals["halftime"]):
            h2_winner = self.team2_goals["name"]
        else:
            h2_winner = "Draw"
        
        final_total = self.team1_goals["final"] + self.team2_goals["final"]
        
        h1_total = self.team1_goals["halftime"] + self.team2_goals["halftime"]
        
        h2_total = (self.team1_goals["final"] - self.team2_goals["halftime"]) + (self.team1_goals["final"] - self.team2_goals["halftime"])
        
        for question in question_list:
            label = question["label"]
            answer = None
                
                
            if label == "h2h":
                mapping = {question[key][0]: key for key in ["opt1", "opt2", "opt3"]}
                answer = mapping.get(winning_team, None)
                
            elif label == "h2h_h1":
                mapping = {question[key][0]: key for key in ["opt1", "opt2", "opt3"]}
                answer = mapping.get(h1_winner, None)
            
            elif label == "h2h_h2":
                mapping = {question[key][0]: key for key in ["opt1", "opt2", "opt3"]}
                answer = mapping.get(h2_winner, None)
                
            elif label == "spreads":
                if winning_team in self.team1_goals.values():
                    spread = self.team1_goals["final"] - self.team2_goals["final"]
                else:
                    spread = self.team2_goals["final"] - self.team1_goals["final"]
                answer = self.spread_helper(winning_team, spread, question)
            
            elif label == "spreads_h2":
                if h2_winner in self.team1_goals.values():
                    spread = (self.team1_goals["final"] - self.team1_goals["halftime"]) - ((self.team2_goals["final"] - self.team2_goals["halftime"]))
                else:
                    spread = (self.team2_goals["final"] - self.team2_goals["halftime"]) - ((self.team1_goals["final"] - self.team1_goals["halftime"]))
                answer = self.spread_helper(h2_winner, spread, question)
            
            elif label == "totals":
                answer = self.totals_helper(question, final_total)
                
            elif label == "totals_h1":
                answer = self.totals_helper(question, h1_total)
            
            elif label == "totals_h2":
                answer = self.totals_helper(question, h2_total)
            
            elif label == "btts":
                answer = "Yes" if (self.team1_goals["final"] > 0 and self.team2_goals["final"] > 0) else "No"

            elif label == "yellow_cards":
                tot_yc = 0
                for team in statistics:
                    for event in team["statistics"]:
                        if event["type"] == "Yellow Cards":
                            tot_yc += event["value"]
                            break
                answer = "opt1" if tot_yc > 5 else "opt2"
                
            elif label == "red_card":
                tot_rc = 0
                for team in statistics:
                    for event in team["statistics"]:
                        if event["type"] == "Red Cards":
                            tot_rc += event["value"]
                            break
                answer = "opt1" if tot_rc > 0 else "opt2" 
            
            # Pass answer into database using Banter API
            data = {
                "api_key": self.BANTER_API_KEY,
                "answer": answer
            }
            url = f"{self.BANTER_API_ENDPOINT}questions/update/{question['questionID']}/"
            
            response = requests.post(url=url,json=data)
        
            if response.status_code == 200:
                print("POST Request | Question Answer -> Database | Successful")
            else:
                print('Request failed with status code:', response.status_code)
        
            return
    
    def spread_helper(self, team_name, goal_diff, data):
        """Spread resolving helper"""
        for key in ["opt1", "opt2"]:
            option_team = data[key][0].split()[0]
            option_spread = float(data[key][0].split()[1])

            if team_name == option_team:
                if team_name == data["opt1"][0].split()[0]:  # If the winning team is the team from opt1
                    if goal_diff >= option_spread:  # Check if they won by at least the spread
                        return key
                else:  # If the winning team is the team from opt2
                    if -goal_diff <= option_spread:  # Check if they won by at least the negative spread
                        return key
        return None

    
    
    def totals_helper(self, data, goals_scored):
        """Totals helper."""
        threshold = float(data["opt1"][0].split()[1])  

        if goals_scored > threshold:
            return "opt1"
        else:
            return "opt2"
        
        
    def question_testing(self, question):
        """Checking the questions"""
        with open("test_file.json", 'a') as file:
            json.dump(question, file, indent = 4, ensure_ascii=False)