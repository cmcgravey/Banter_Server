"""In-game Session Backend."""
import requests
import json
import random
import time
import logging
import re

LOGGER = logging.getLogger(__name__)

class gameSession:
    def __init__(self, gameID, team1_id, team2_id):
        """In-Game Thread. Check game times and send filled-out questions to database periodically."""
        self.game_status = "PENDING"
        self.game_time = 0
        self.game_stage = "NS"

        self.DEBUG = False
        self.DEBUG_HT = True
        self.debug_index = 1
        
        self.gameID = gameID
        

        self.prem_league_id = 39
        self.MLS_id = 253
        self.league_id = 253
        
        self.BANTER_API_KEY = "87ab0a3db51d297d3d1cf2d4dcdcb71b"
        self.BANTER_API_ENDPOINT = "https://www.banter-api.com/api/"
        
        
        # Team 1 is always home team
        
        team1_url = f"{self.BANTER_API_ENDPOINT}teams/{team1_id}/?api_key={self.BANTER_API_KEY}"
        team2_url = f"{self.BANTER_API_ENDPOINT}teams/{team2_id}/?api_key={self.BANTER_API_KEY}"
        
        team1_response = requests.get(url=team1_url).json()
        team2_response = requests.get(url=team2_url).json()
        
        self.team1 = team1_response["name"]
        self.team2 = team2_response["name"]
        
        self.h2h_enumeration = {
            "Home": self.team1,
            "Away": self.team2,
            "Draw": "Draw"
        }
        
        LOGGER.info(f"{self.team1}")
        LOGGER.info(f"{self.team2}")
        
        self.fixture_id = self.locate_fixture_id()
        self.fixture_id = "1139504"
        self.team1_score = 0
        self.team2_score = 0
        
        self.halftime_corners = 0
        
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
        
        
        self.non_book_questions = ["yellow_cards", "red_card"]
        # Add in: Answer Options, gain/loss for answer
        self.question_templates = {}
        self.question_templates["pregame"] = [
            {"question_stage": "pregame",
             "label": "Match Winner", 
             "question": "Who's going to win?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "Goals Over/Under",
             "question": "Total goals in game?",
             "Game_id": self.gameID},
            
             {"question_stage": "pregame",
             "label": "Goals Over/Under First Half",
             "question": "Total goals in first half?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "Both Teams Score",
             "question": "Will both teams score in this match?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "Both Teams Score - First Half",
             "question": "Will both teams score in the first half?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "red_card",
             "question": "Will there be a red card this game?",
             "Game_id": self.gameID},
            
            {"question_stage": "pregame",
             "label": "yellow_cards",
             "question": "Will there be over 5 yellow cards played?",
             "Game_id": self.gameID},
            
             {"question_stage": "pregame",
             "label": "Odd/Even",
             "question": "Odd/Even Total Goals Scored?",
             "Game_id": self.gameID},
             
             {"question_stage": "pregame",
             "label": "Corners Over Under",
             "question": "How many Corner Kicks?",
             "Game_id": self.gameID},
           
        ]
        
        self.question_templates["ingame"] = [
            
            {"question_stage": "ingame",
             "label": "Total Corners (3 way) (1st Half)",
             "question": "How Many Corner Kicks in 1st half?",
             "Game_id": self.gameID},
            
            {"question_stage": "ingame",
             "label": "Over/Under (1st Half)",
             "question": "How many goals will there be at the end of the half?",
             "Game_id": self.gameID},
            
        ]
        
        self.question_templates["halftime"] = [
            {"question_stage": "halftime",
             "label": "To Win 2nd Half",
             "question": "Who's winning the 2nd Half?",
             "Game_id": self.gameID},
            
            {"question_stage": "halftime",
             "label": "Both Teams To Score (2nd Half)",
             "question": "Will both teams score in 2nd Half?",
             "Game_id": self.gameID},
            
            {"question_stage": "halftime",
             "label": "Away Team Score a Goal (2nd Half)",
             "question": "Will the Away Team score in the 2nd Half?",
             "Game_id": self.gameID},
            
            
            {"question_stage": "halftime",
             "label": "Home Team Score a Goal (2nd Half)",
             "question": "Will the Home Team score in the 2nd Half?",
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
                self.update_game_status()
                self.track_game_time()
        else:
            self.update_game_status()
            time.sleep(120)
            self.game_status = "IN_PLAY"
            self.game_stage = "1H"
        
        if self.game_stage == "SUSP" or self.game_stage == "PST" or self.game_stage == "CANC":
            LOGGER.info("Match cancelled")
            return
        ingame_flag = False
        halftime_flag = False
        if self.game_stage == "1H":
            self.game_status = "IN_PLAY"
            while self.game_status == "IN_PLAY" or self.game_status == "HALFTIME":
                # Check for game time
                self.track_game_time()
                self.update_game_status()
                LOGGER.info(f"Loop {self.debug_index}")
                self.debug_index += 1
                if 20 <= self.game_time <= 30 and self.game_stage == "1H" and ingame_flag == False:
                    ingame_flag = True
                    self.build_questions("ingame")
                    LOGGER.info("Creating ingame questions")
                    
                elif self.game_stage == "HT" and halftime_flag == False:
                    self.halftime_corners = self.update_corners()
                    self.build_questions("halftime")
                    LOGGER.info("Creating halftime questions")
                    self.update_scores("halftime")
                    halftime_flag = True
                if self.DEBUG == True:
                    time.sleep(10)
                else:
                    time.sleep(60)
            self.update_scores("final")
            self.update_game_status()
            self.resolve_questions()
        return
    
    def update_scores(self, stage):
        """Keep data for the score at halftime for reference for answering questions."""
        self.team1_goals[stage] = self.team1_score
        self.team2_goals[stage] = self.team2_score
    
    def build_questions(self, question_stage):
        """Build questions based off of sports odds."""
        
        staged_questions = random.sample(self.question_templates[question_stage], 1)
        
        sportsbook_data = self.get_sports_odds(question_stage)
        
        # Build each question sequentially
        for i in range(len(staged_questions)):
            # Do different calculation for red and yellow cards, not based on sportsbook odds
            if staged_questions[i]["label"] == "yellow_cards" or staged_questions[i]["label"] == "red_card":
                # (Question text, points gained if correct, points lost if wrong)
                rewards, pens = self.calculate_banter_points([1, 1])
                staged_questions[i]["opt1"] = ("Yes", rewards[0], pens[0])
                staged_questions[i]["opt2"] = ("No", rewards[1], pens[1])
            else:
                if question_stage == "pregame":
                    question_odds = self.find_market(sportsbook_data["bookmakers"], staged_questions[i])
                else:
                    question_odds = self.find_live_market(sportsbook_data["odds"], staged_questions[i])
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
                        
            self.add_question(staged_questions[i])      
    
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
                    
    def find_live_market(self, odds, question):
        """For live questions ingame, find the market pertaining to the question asked."""
        for odd in odds:
            if odd["name"] == question["label"]:
                if question["label"].startswith("Over/Under"):
                    return odd["values"][:2]
                else:
                    return odd["values"]
                
        
    
    def get_sports_odds(self, stage):
        if stage == "pregame":
            url = "https://api-football-v1.p.rapidapi.com/v3/odds/"
        else:
            url = "https://api-football-v1.p.rapidapi.com/v3/odds/live"
        query = {"fixture": self.fixture_id}
        headers = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=query)
        return response.json()["response"][0] # Returns all bookmakers and potential odds

        
    def add_question(self, question):
        """Once Questions are built, insert them back into database using banter API."""

        question["api_key"] = self.BANTER_API_KEY
        
        question_url = f"{self.BANTER_API_ENDPOINT}questions/{self.gameID}/"

        response = requests.post(url=question_url,json=question)
        
        if response.status_code == 200:
            print("POST Request | Question -> Database | Successful")
        else:
            print('Request failed with status code:', response.status_code)
            
        if self.DEBUG == True:
            answer_url = f"{self.BANTER_API_ENDPOINT}answers/{response.json()['questionID']}/1/"
            input = {"api_key": self.BANTER_API_KEY, "answer": "opt1"}
            response = requests.post(url=answer_url, json=input)
            print("POST Request | User Answer -> Database | Successful")
    
        
        
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
        short_data = data["response"][0]["fixture"]["status"]["short"]
        self.game_time = data["response"][0]["fixture"]["status"]["elapsed"]
        self.game_stage = short_data
        if short_data == "FT" or short_data == "AET" or short_data == "PEN":
            self.game_status = "FINISHED"
        elif short_data == "HT":
            self.game_status = "HALFTIME"
        elif short_data == "NS":
            self.game_status = "PREGAME"   
        else:
            self.game_status = "IN_PLAY"     
        self.team1_score = data["response"][0]["goals"]["home"]
        self.team2_score = data["response"][0]["goals"]["away"]
        return
    
    def locate_fixture_id(self):
        """Locate the fixture ID for the Rapids API - Football API."""
        url = "https://api-football-v1.p.rapidapi.com/v3/fixtures"

        headers = {
            "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
            "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        
        query = {"league": str(self.league_id), "status": "NS", "season": "2023"}
        
        if self.DEBUG == True:
            with open(f"BNTRserver/testing/locate_fixture_id.json", 'r') as file:
                data = json.load(file)
        else:
            response = requests.get(url, headers=headers, params=query)
            data = response.json()

        for response in data["response"]:
            home = response["teams"]["home"].values()
            away = response["teams"]["away"].values()
            if (self.team1 in home or self.team2 in home) and (self.team1 in away or self.team2 in away):
                return response["fixture"]["id"]
    
    def update_game_status(self):
        url = f"{self.BANTER_API_ENDPOINT}games/{self.gameID}/"
        
        data = {
            "api_key": self.BANTER_API_KEY,
            "update": [self.team1_score, self.team2_score, f"{self.game_time}:00"],
            "status": self.game_status
        }
        
        response = requests.post(url=url, json=data)
        return

    def update_corners(self):
        """Update halftime corners."""
        stat_url = "https://api-football-v1.p.rapidapi.com/v3/fixtures/statistics"
        
        querystring = {"fixture": f"{self.fixture_id}"}
        
        headers = {
                "X-RapidAPI-Key": "7495251faemshb5e0890629c8956p1d9b37jsn1f10ba9b5f5e",
                "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
        }
        response = requests.get(url=stat_url,headers=headers,params=querystring)
        
        statistics = response.json()["response"]
        
        
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
            with open(f"BNTRserver/testing/postgame_statistics.json", 'r') as file:
                statistics = json.load(file)["response"]
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
            
        corners = 0
        for team in statistics:
            for event in team["statistics"]:
                if event["type"] == "Corner Kicks":
                    val = 0 if event["value"] is None else event["value"]
                    corners += val
        
        final_total = self.team1_goals["final"] + self.team2_goals["final"]
        
        h1_total = self.team1_goals["halftime"] + self.team2_goals["halftime"]
        
        h2_total = (self.team1_goals["final"] - self.team2_goals["halftime"]) + (self.team1_goals["final"] - self.team2_goals["halftime"])
        for question in question_list:
            label = question["label"]
            answer = None
                
            if label == "Match Winner":
                answer = f"opt{question['options'].index(winning_team) + 1}"
                
            elif label == "Goals Over/Under":
                answer = self.totals_helper(question, final_total)
            
            elif label == "Goals Over/Under First Half" or label == "Over/Under (1st Half)":
                answer = self.totals_helper(question, h1_total)
                
            elif label == "Both Teams Score":
                answer = "opt1" if (self.team1_goals["final"] > 0 and self.team2_goals["final"] > 0) else "opt2"
                
            elif label == "Both Teams Score - First Half":
                answer = "opt1" if (self.team1_goals["halftime"] > 0 and self.team2_goals["halftime"] > 0) else "opt2"

            elif label == "Odd/Even":
                answer = "opt1" if final_total % 2 != 0 else "opt2"
            
            elif label == "Total Corners (3 way) (1st Half)":
                answer = self.corners_helper(question)
            
            elif label == "To Win 2nd Half":
                answer = f"opt{question['options'].index(h2_winner) + 1}"
                
            elif label == "Both Teams To Score (2nd Half)":
                answer = "opt1" if (self.team1_goals["final"] - self.team1_goals["halftime"]) > 0 and (self.team2_goals["final"] - self.team2_goals["halftime"]) else "opt2"
                
            elif label == "Away Team Score a Goal (2nd Half)":
                answer = "opt1" if (self.team2_goals["final"] - self.team2_goals["halftime"]) > 0 else "opt2"
                
            elif label == "Home Team Score a Goal (2nd Half)":
                answer = "opt1" if (self.team1_goals["final"] - self.team2_goals["halftime"]) > 0 else "opt2"
                
            elif label == "yellow_cards":
                tot_yc = 0
                for team in statistics:
                    for event in team["statistics"]:
                        if event["type"] == "Yellow Cards":
                            val = 0 if event["value"] is None else event["value"]
                            tot_yc += val
                answer = "opt1" if tot_yc > 5 else "opt2"
                
            elif label == "red_card":
                tot_rc = 0
                for team in statistics:
                    for event in team["statistics"]:
                        if event["type"] == "Red Cards":
                            val = 0 if event["value"] is None else event["value"]
                            tot_rc += val
                answer = "opt1" if tot_rc > 0 else "opt2" 
                
            elif label == "Corners Over Under":
                corners = 0
                for team in statistics:
                    for event in team["statistics"]:
                        if event["type"] == "Corner Kicks":
                            val = 0 if event["value"] is None else event["value"]
                            corners += val
                answer = "opt1" if corners > float(question["options"][0].split()[1]) else "opt2"
            else:
                answer = "opt1"
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
                print('Request failed with status code:', response.status_code)
        return
    
    def totals_helper(self, question, total_goals):
        """Totals helper."""
        threshold = float(question['options'][0].split()[1])
        
        if total_goals > threshold:
            return "opt1"  
        else:
            return "opt2" 
    
    def corners_helper(self, question):
        """3 Way Corners Helper."""
        threshold = float(question['options'][0].split()[1])
        
        if self.halftime_corners > threshold:
            return "opt1"
        elif self.halftime_corners < threshold:
            return "opt3"
        else:
            return "opt2"
        
    def question_testing(self, question):
        """Checking the questions"""
        with open("test_file.json", 'a') as file:
            json.dump(question, file, indent = 4, ensure_ascii=False)

