"""In-game Session Backend."""
import requests
import json
import random
import time
import logging

LOGGER = logging.getLogger(__name__)

class gameSession:
    def __init__(self, gameID, team1_id, team2_id, fixtureID):
        """In-Game Thread. Check game times and send filled-out questions to database periodically."""
        self.game_status = "PENDING"
        self.game_time = 0
        self.game_stage = "NS"
        
        self.DEBUG = True
        self.DEBUG_HT = True
        self.debug_index = 1
        
        self.gameID = gameID
        
        league_ids = {
            "MLS": 253,
            "PREMIER": 39
        }
        
        self.BANTER_API_KEY = "87ab0a3db51d297d3d1cf2d4dcdcb71b"
        self.BANTER_API_ENDPOINT = "https://www.banter-api.com/api/"
        
        game_url = f"{self.BANTER_API_ENDPOINT}games/{gameID}/?api_key={self.BANTER_API_KEY}"
        
        game_response = requests.get(url=game_url).json()
        
        league = game_response["league"]
        
        self.league_id = league_ids[league]
        
        team1_url = f"{self.BANTER_API_ENDPOINT}teams/{team1_id}/?api_key={self.BANTER_API_KEY}"
        team2_url = f"{self.BANTER_API_ENDPOINT}teams/{team2_id}/?api_key={self.BANTER_API_KEY}"
        
        team1_response = requests.get(url=team1_url).json()
        team2_response = requests.get(url=team2_url).json()
        
        self.team1 = team1_response["name"]
        self.team2 = team2_response["name"]
        
        self.h2h_enumeration = {
            "Home": team1_response["name"],
            "Away": team2_response["name"],
            "Draw": "Draw"
        }
        
        LOGGER.info(f"{self.team1}")
        LOGGER.info(f"{self.team2}")
        
        self.fixture_id = fixtureID
        self.team1_score = 0
        self.team2_score = 0

        self.card_template = {
            "red_card": ["Over 0.5", "Under 0.5"],
            "yellow_cards": ["Over 4", "Under 4"]
        }

        self.game_statistics = {
            "O/U":{
                "corners_ft": 0,
                "corners_ht": 0,
                "goals_h1": 0,
                "goals_h2": 0,
                "goals_total": 0,
                "red_cards": 0,
                "yellow_cards": 0
            },
            "team1": {
                "halftime": 0,
                "final": 0,
                "2nd_half": 0,
                "name": self.team1
            },
            "team2": {
                "halftime": 0,
                "final": 0,
                "2nd_half": 0,
                "name": self.team2
            },

        }
        


        
        self.non_book_questions = ["yellow_cards", "red_card"]
        # Add in: Answer Options, gain/loss for answer
        self.question_templates = {}
        self.question_templates["pregame"] = [
            {"question_stage": "pregame",
             "label": "Match Winner", 
             "question": "Who's going to win?",
             "type": "h2h",
             "tag": "final",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "Goals Over/Under",
             "question": "Total goals in game?",
             "type": "O/U",
             "tag": "goals_total",
             "Game_id": self.gameID},
            
             {"question_stage": "pregame",
             "label": "Goals Over/Under First Half",
             "question": "Total goals in first half?",
             "type": "O/U",
             "tag": "goals_h1",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "Both Teams Score",
             "question": "Will both teams score in this match?",
             "type": "btts",
             "tag": "final",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "Both Teams Score - First Half",
             "question": "Will both teams score in the first half?",
             "type": "btts",
             "tag": "halftime",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "red_card",
             "question": "How Many Red Cards?",
             "type": "O/U",
             "tag": "red_cards",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "yellow_cards",
             "question": "How Many Yellow Cards?",
             "type": "O/U",
             "tag": "yellow_cards",
             "Game_id": self.gameID},
            
             {"question_stage": "pregame",
             "label": "Odd/Even",
             "question": "Odd/Even Total Goals Scored?",
             "type": "Odd/Even",
             "tag": "Null",
             "Game_id": self.gameID},
             
             {"question_stage": "pregame",
             "label": "Corners Over Under",
             "question": "How many Corner Kicks?",
             "type": "O/U",
             "tag": "corners_ft",
             "Game_id": self.gameID},
           
        ]
        
        self.question_templates["ingame"] = [
            
            {"question_stage": "ingame",
             "label": "Total Corners (3 way) (1st Half)",
             "question": "How Many Corner Kicks in 1st half?",
             "type": "O/U 3 Way",
             "tag": "corners_ht",
             "Game_id": self.gameID},
            
            {"question_stage": "ingame",
             "label": "Over/Under (1st Half)",
             "question": "How many goals will there be at the end of the half?",
             "type": "O/U",
             "tag": "goals_h1",
             "Game_id": self.gameID},

             {"question_stage": "ingame",
             "label": "Goals Odd/Even",
             "question": "Odd/Even Goals Scored?",
             "type": "Odd/Even",
             "tag": "Null",
             "Game_id": self.gameID},
            
        ]
        
        self.question_templates["halftime"] = [
            {"question_stage": "halftime",
             "label": "To Win 2nd Half",
             "question": "Who's winning the 2nd Half?",
             "type": "h2h",
             "tag": "2nd_half",
             "Game_id": self.gameID},
            
            {"question_stage": "halftime",
             "label": "Both Teams To Score (2nd Half)",
             "question": "Will both teams score in 2nd Half?",
             "type": "btts",
             "tag": "2nd_half",
             "Game_id": self.gameID},
            
            {"question_stage": "halftime",
             "label": "Away Team Score a Goal (2nd Half)",
             "question": "Will the Away Team score in the 2nd Half?",
             "type": "to_score",
             "tag": "team2",
             "Game_id": self.gameID},
            
            
            {"question_stage": "halftime",
             "label": "Home Team Score a Goal (2nd Half)",
             "question": "Will the Home Team score in the 2nd Half?",
             "type": "to_score",
             "tag": "team1",
             "Game_id": self.gameID}
        ]
    def run_game_session(self):
        """Main thread for running the game"""
        self.build_questions("pregame")
        LOGGER.info("Creating pregame questions")
        self.game_stage = "NS"
        self.game_status = "PREGAME"
        
        if self.DEBUG == False:
            while self.game_stage == "NS":
                self.track_game_time()
                time.sleep(15)
        else:
            self.update_game_status()
            time.sleep(10)
            self.game_status = "IN_PLAY"
            self.game_stage = "1H"
     
        if self.game_stage == "SUSP" or self.game_stage == "PST" or self.game_stage == "CANC":
            LOGGER.info("Match cancelled")
            return
        
        ingame_flag = False
        halftime_flag = False
        
        lock_ingame = False
        lock_halftime = False
        if self.game_stage == "1H":
            
            self.lock_questions("pregame")
            self.game_status = "IN_PLAY"
            
            while self.game_status == "IN_PLAY" or self.game_status == "HALFTIME":
                # Check for game time
                self.track_game_time()
                self.update_game_status()
                LOGGER.info(f"Loop {self.debug_index}")
                self.debug_index += 1
                
                if 20 <= self.game_time <= 25 and self.game_stage == "1H" and ingame_flag == False:
                    ingame_flag = True
                    self.build_questions("ingame")
                    LOGGER.info("Creating ingame questions")
                    
                elif self.game_time > 25 and lock_ingame == False:
                    self.lock_questions("ingame")
                    lock_ingame = True
                    
                elif self.game_stage == "HT" and halftime_flag == False:
                    self.game_statistics["O/U"]["corners_ht"] = self.update_corners()
                    self.build_questions("halftime")
                    LOGGER.info("Creating halftime questions")
                    self.update_scores("halftime")
                    halftime_flag = True
                    
                elif self.game_stage == "2H" and lock_halftime == False:
                    self.lock_questions("halftime")
                    lock_halftime = True
                    
                time.sleep(10) if self.DEBUG == True else time.sleep(60)
                
            self.update_scores("final")
            self.update_game_status()
            self.resolve_questions()
        return
    
    def update_scores(self, stage):
        """Keep data for the score at halftime for reference for answering questions."""
        self.game_statistics["team1"][stage] = self.team1_score
        self.game_statistics["team2"][stage] = self.team2_score

        if stage == "final":
            self.game_statistics["team1"]["2nd_half"] = self.team1_score - self.game_statistics["team1"]["halftime"]
            self.game_statistics["team2"]["2nd_half"] = self.team2_score - self.game_statistics["team2"]["halftime"]
    def build_questions(self, question_stage):
        """Build questions based off of sports odds."""
        if question_stage == "ingame":
            num_questions = 1
        else:
            num_questions = 2

        staged_questions = random.sample(self.question_templates[question_stage], num_questions)
        sportsbook_data = self.get_sports_odds(question_stage)
        LOGGER.info(question_stage)
        # Build each question sequentially
        for i in range(len(staged_questions)):
            # Do different calculation for red and yellow cards, not based on sportsbook odds
            if staged_questions[i]["label"] == "yellow_cards" or staged_questions[i]["label"] == "red_card":
                # (Question text, points gained if correct, points lost if wrong)
                rewards, pens = self.calculate_banter_points([1, 1])
                qs = self.card_template[staged_questions[i]["label"]]
                staged_questions[i]["opt1"] = (qs[0], rewards[0], pens[0])
                staged_questions[i]["opt2"] = (qs[1], rewards[1], pens[1])
            else:
                if question_stage == "pregame":
                    question_odds = self.find_market(sportsbook_data["bookmakers"], staged_questions[i])
                else:
                    question_odds = self.find_live_market(sportsbook_data["odds"], staged_questions[i])
                    
                if question_odds is None:
                    LOGGER.info("Cannot find a market for posed question. Retrying with new question")
                    self.build_questions(question_stage=question_stage)
                    return
                rewards, pens = self.calculate_banter_points([float(odds["odd"]) for odds in question_odds])

                for j in range(len(rewards)):
                    # These question labels don't require points in the question text
                    if staged_questions[i]["label"].startswith("Match"):
                        # Match Winner - H2H
                        staged_questions[i][f"opt{j+1}"] = (f"{self.h2h_enumeration[question_odds[j]['value']]}", int(rewards[j]), int(pens[j]))
                    elif question_stage == "ingame":
                        staged_questions[i][f"opt{j+1}"] = (f"{question_odds[j]['value']} {question_odds[j]['handicap']}", int(rewards[j]), int(pens[j]))
                    elif question_stage == "halftime" and (question_odds[j]['value'] == "Home" or question_odds[j]['value'] == "Away"):
                         staged_questions[i][f"opt{j+1}"] = (f"{self.h2h_enumeration[question_odds[j]['value']]}", int(rewards[j]), int(pens[j]))
                    else:
                         staged_questions[i][f"opt{j+1}"] = (f"{question_odds[j]['value']}", int(rewards[j]), int(pens[j]))
            staged_questions[i]["status"] = "OPEN"
            self.add_question(staged_questions[i])
        return     
    
    def calculate_banter_points(self, odds_list):
        """Calculate banter points earned/lost based on converting US Moneyline to probability."""
        probabilities = [1 / o for o in odds_list]
        margin = sum(probabilities)
        # Adjust probabilities for the margin
        adjusted_probabilities = [p / margin for p in probabilities]
        # Find the scale factor
        # Calculate points for each odd and their corresponding loss
        points_for_correct = [(10 + 40) * p for p in adjusted_probabilities]
        # Calculate loss for each (1/5 of the reward)
        loss_for_incorrect = [points / 5 for points in points_for_correct]
        return points_for_correct, loss_for_incorrect

                               
    def find_market(self, bookmakers, question):
        """Find a bookmaker that has the specific market question we are asking."""
        for bookmaker in bookmakers:
            for market in bookmaker["bets"]:
                if market["name"] == question["label"]:
                    if question["label"].startswith("Goals") or question["label"].startswith("Corners"):
                        # Only get the first values appeared.
                        return market["values"][:2]
                    else:
                        return market["values"]
        return None
                    
    def find_live_market(self, odds, question):
        """For live questions ingame, find the market pertaining to the question asked."""
        for odd in odds:
            if odd["name"] == question["label"]:
                if question["label"].startswith("Over/Under"):
                    return odd["values"][:2]
                else:
                    return odd["values"]
        return None
                
        
    
    def get_sports_odds(self, stage, max_attempts=5, delay=8):
        if stage == "pregame":
            url = "https://api-football-v1.p.rapidapi.com/v3/odds/"
        else:
            url = "https://api-football-v1.p.rapidapi.com/v3/odds/live"
        query = {"fixture": self.fixture_id}
        headers = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        if self.DEBUG == True:
            if stage == "pregame":
                with open("BNTRserver/testing/pregame_odds.json", 'r') as file:
                    data = json.load(file)
                    output = data["response"][0]
                    return output
            else:
                with open("BNTRserver/testing/live_odds.json", 'r') as file:
                    data = json.load(file)
                    output = data["response"][0]
                    return output

        
        for attempt in range(max_attempts): # This is essential data. Retry 5 times before failing program.
            
            try:
                response = requests.get(url, headers=headers, params=query)
                output = response.json()["response"][0]
                return output
            except (KeyError, IndexError):
                if attempt < max_attempts - 1:
                    time.sleep(delay)  # delay before retrying. Give it longer delay, more room for error
                else:
                    LOGGER.info("Sports odds API failed")
                    return  # re-raise the exception if all retries fail
        
    def add_question(self, question):
        """Once Questions are built, insert them back into database using banter API."""

        question["api_key"] = self.BANTER_API_KEY
        
        question_url = f"{self.BANTER_API_ENDPOINT}questions/{self.gameID}/"

        response = requests.post(url=question_url,json=question)
        
        if response.status_code == 200:
            print("POST Request | Question -> Database | Successful")
        else:
            print('POST Request | Question -> Database | Request failed with status code:', response.status_code)
        
        
    def track_game_time(self):
        """Use Rapid API for current game time. Called every minute."""
            
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"
        
        # FOR TEST: Fixture Id: 1132545
        
        query = {"id": f"{self.fixture_id}"}
        
        headers = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        if self.DEBUG == True:
            with open(f"BNTRserver/testing/track_game_time_{self.debug_index}.json", 'r') as file:
                data = json.load(file)
        else:
            response = requests.get(url, headers=headers, params=query)
            data = response.json()
        
        try: # Non essential data to the program. Can be passed.
            data = data["response"][0]
            short_data = data["fixture"]["status"]["short"]
            self.game_time = data["fixture"]["status"]["elapsed"]
            self.game_stage = short_data
            
            status_enumeration = {
                "FT": "FINISHED",
                "AET": "FINISHED",
                "PEN": "FINISHED",
                "HT": "HALFTIME",
                "NS": "PREGAME"
            }
            if short_data in status_enumeration:
                self.game_status = status_enumeration[short_data]
            else:
                self.game_status = "IN_PLAY"   
            self.team1_score = data["goals"]["home"]
            self.team2_score = data["goals"]["away"]
            LOGGER.info(f"Tracking game time. Status: {self.game_status}. Stage:{self.game_stage}")
        except (KeyError, IndexError):
            pass 
        return
    
    def update_game_status(self):
        url = f"{self.BANTER_API_ENDPOINT}games/{self.gameID}/"
        
        data = {
            "api_key": self.BANTER_API_KEY,
            "update": [self.team1_score, self.team2_score, f"{self.game_time}:00"],
            "status": self.game_status
        }

        response = requests.post(url=url, json=data)
        
        if response.status_code == 200:
            print("POST Request | Game Status -> Database | Successful")
        else:
            print('POST Request | Game Status -> Database | Request failed with status code:', response.status_code)
        
        return

    def update_corners(self, max_attempts=5, delay=5):
        """Update halftime corners."""
        stat_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"
        
        querystring = {"fixture": f"{self.fixture_id}"}
        
        headers = {
                "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        if self.DEBUG == True:
            with open ("BNTRserver/testing/ingame_statistics.json", 'r') as f:
                data = json.load(f)
                stats = data["response"]
                corners = self.stat_helper(stats, "Corner Kicks")
                return corners
       
        for attempt in range(max_attempts): # Essential data. Limited retries.
            try:
                response = requests.get(url=stat_url,headers=headers,params=querystring)
                statistics = response.json()["response"]
                corners = self.stat_helper(statistics, "Corner Kicks")
                return corners
            except KeyError:
                if attempt < max_attempts - 1:
                    time.sleep(delay)  # wait for 2 seconds before retrying
                else:
                    return 0 # re-raise the exception if all retries fail      
        
        
        
    def resolve_questions(self):
        """Pull the questions from the database with a specific gameID, then post answer to Banter API."""
        
        # Fetch all questions from database
        
        api_url = f"{self.BANTER_API_ENDPOINT}questions/{self.gameID}/?api_key={self.BANTER_API_KEY}"
        
        
        response = requests.get(url=api_url)
        
        question_list = response.json()["questions"]
        
        # Fetching game statistics now from Rapid API
        
        stat_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"
        
        querystring = {"fixture": f"{self.fixture_id}"}
        
        headers = {
                "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        if self.DEBUG == True:
            with open("BNTRserver/testing/postgame_statistics.json", 'r') as file:
                statistics = json.load(file)["response"]
        else:
            for attempt in range(5): # Essential data. Return function and don't resolve answers if failed 5 times. 
                try:
                    response = requests.get(stat_url, headers=headers, params=querystring)
                    statistics = response.json()["response"]
                except KeyError:
                    if attempt < 4:
                        time.sleep(5)  # wait for 5 seconds before retrying
                    else:
                        LOGGER.info("statistics API failed")
                        return  # re-raise the exception if all retries fail     
        
        self.update_stats(statistics)
      
        # Use questions and statistics to find answers and input back into database.
        team1_goals = self.game_statistics["team1"]
        team2_goals = self.game_statistics["team2"]
        if team1_goals["final"] == team2_goals["final"]:
            winning_team = "Draw"
        else:
            winning_team = max(team1_goals, team2_goals, key=lambda team: team["final"])["name"]
        
        if (team1_goals["2nd_half"]) == (team2_goals["2nd_half"]):
            h2_winner = "Draw"
        else:
            h2_winner = max(team1_goals, team2_goals, key=lambda team: team["2nd_half"])["name"]

        final_total = team1_goals["final"] + team2_goals["final"]
        h2h_enum = {
            "final": winning_team,
            "2nd_half": h2_winner
        }
        
        for question in question_list:
            label = question["label"]
            type = question["type"]
            tag = question["tag"]
            answer = None

            if type == "O/U":
                answer = self.totals_helper(question, self.game_statistics[type][tag])

            elif type == "O/U 3 Way":
                answer = self.corners_helper(question)

            elif type == "btts":
                answer = self.btts_helper(tag)
            
            elif type == "to_score":
                answer = "opt1" if self.game_statistics[tag]["2nd_half"] > 0 else "opt2"
            
            elif type == "h2h":
                answer = f"opt{question['options'].index(h2h_enum[tag]) + 1}"

            elif type == "Odd/Even":
                answer = "opt1" if final_total % 2 != 0 else "opt2"

            else:
                answer = "opt1"

            print(label, answer)
            # Post answer into database using Banter API
            data = {
                "api_key": self.BANTER_API_KEY,
                "answer": answer
            }
            url = f"{self.BANTER_API_ENDPOINT}questions/update/{question['questionID']}/"
            
            response = requests.post(url=url,json=data)
        
            if response.status_code == 200:
                print("POST Request | Question Answer -> Database | Successful")
            else:
                print('POST Request | Question Answer -> Database | Request failed with status code:', response.status_code)
        return
    
    def stat_helper(self, stats, key):
        return sum(
        (statistic['value'] for team in stats
         for statistic in team['statistics']
         if statistic['type'] == key and statistic['value'] is not None),
        0  # Start the sum at 0
        )
        
    def lock_questions(self, stage):
        
        url = f"{self.BANTER_API_ENDPOINT}questions/{self.gameID}/{stage}/"
        
        data = {
            "api_key": self.BANTER_API_KEY,
        } 
        response = requests.post(url=url, json=data)
        
        if response.status_code == 200:
            print("POST Request | Question Lock -> Database | Successful")
        else:
            print('Request failed with status code:', response.status_code)
        
    def update_stats(self, stats):
        if self.DEBUG == True:
            self.game_statistics["team1"]["halftime"] = 2
            self.game_statistics["team2"]["halftime"] = 0
            self.game_statistics["team1"]["final"] = 3
            self.game_statistics["team2"]["final"] = 2
            self.game_statistics["team1"]["2nd_half"] = 1
            self.game_statistics["team2"]["2nd_half"] = 2

        self.game_statistics["O/U"]["red_cards"] = self.stat_helper(stats, "Red Cards")
        self.game_statistics["O/U"]["yellow_cards"] = self.stat_helper(stats, "Yellow Cards")
        self.game_statistics["O/U"]["corners_ft"] = self.stat_helper(stats, "Corner Kicks")

        self.game_statistics["O/U"]["goals_h1"] = self.game_statistics["team1"]["halftime"] + self.game_statistics["team2"]["halftime"]
        self.game_statistics["O/U"]["goals_h2"] = self.game_statistics["team1"]["2nd_half"] + self.game_statistics["team2"]["2nd_half"]
        self.game_statistics["O/U"]["goals_total"] = self.game_statistics["team1"]["final"] + self.game_statistics["team2"]["final"]


    def totals_helper(self, question, total):
        """Totals helper."""
        threshold = float(question['options'][0].split()[1])
        
        if total > threshold:
            return "opt1"  
        else:
            return "opt2" 
    
    def corners_helper(self, question):
        """3 Way Corners Helper."""
        threshold = float(question['options'][0].split()[1])
        
        if self.game_statistics["O/U"]["corners_ht"] > threshold:
            return "opt1"
        elif self.game_statistics["O/U"]["corners_ht"] < threshold:
            return "opt3"
        else:
            return "opt2"
    
    def btts_helper(self, tag):
        return "opt1" if ((self.game_statistics["team1"][tag] > 0) and (self.game_statistics["team2"][tag] > 0)) else "opt2"

        
    def question_testing(self, question):
        """Checking the questions"""
        with open("test_file.json", 'a') as file:
            json.dump(question, file, indent = 4, ensure_ascii=False)

