"""In-game Session Backend."""
import requests
import json
import random



class gameSession:
    def __init__(self, gameID):
        """In-Game Thread. Check game times and send filled-out questions to database periodically."""
        self.game_status = None
        self.event_id = None
        self.team_1 = ""
        self.team_2 = ""
        self.gameID = gameID
        self.question_templates = {}
        # Add in: Answer Options, gain/loss for answer
        self.question_templates["pregame"] = [
            {"question_stage": "Pregame",
             "label": "spreads",
             "question": "Predict the Spread",
             "Game_id": self.gameID},
            
            {"question_stage": "Pregame",
             "label": "h2h",
             "question": "Who's going to win?",
             "Game_id": self.gameID},
            
            {"question_stage": "Pregame",
             "label": "totals",
             "question": "How many goals will be scored?",
             "Game_id": self.gameID},
            
            {"question_stage": "Pregame",
             "label": "yellow_cards",
             "question": "Will there be over 5 yellow cards played?",
             "Game_id": self.gameID},
            
            {"question_stage": "Pregame",
             "label": "btts",
             "question": "Will both teams score?",
             "Game_id": self.gameID},
            
            {"question_stage": "Pregame",
             "label": "red_card",
             "question": "Will there be a red card this game?",
             "Game_id": self.gameID}
        ]
        
        self.question_templates["ingame"] = [
            {"question_stage": "ingame",
             "label": "h2h",
             "question": "Which team is scoring the next goal?",
             "Game_id": self.gameID},
            
            {"question_stage": "ingame",
             "label": "h2h",
             "question": "Who's going to win?",
             "Game_id": self.gameID},
            
            {"question_stage": "ingame",
             "label": "totals_h1",
             "question": "How many goals will there be for the rest of the half?",
             "Game_id": self.gameID},
            
            {"question_stage": "ingame",
             "label": "h2h_h1",
             "question": "Which team will score a goal this half?",
             "Game_id": self.gameID}
            
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
        
    def build_questions(self, question_stage):
        """Build questions based off of sports odds"""
        sportsbook_data = []
        if question_stage == "pregame":
            staged_questions = random.sample(self.question_templates["pregame"], 2)
        elif question_stage == "ingame":
            staged_questions = random.sample(self.question_templates["ingame"], 2)
        else:
            staged_questions = random.sample(self.question_templates["halftime"], 2)
            
        markets = [question["label"] for question in staged_questions] 
        
        # Remove non-sportsbook related questions    
        if "next_goal" in markets:
            markets.remove("next_goal")
        if "yellow_cards" in markets:
            markets.remove("yellow_cards")
        if "red_card" in markets:
            markets.remove("red_card")
        # Call sportsbook API to get data
        if len(markets) > 0:
            sportsbook_data = self.callSportsbookAPI(self.get_event_id(), markets)
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
            self.question_testing(staged_questions[i])      
    
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
        
    def get_event_id(self):
        """Get event ID from game ID (From the Odds API), in order to fetch unique sports Odds."""
        return "4026494a30d50d6e544312b4110353da"
    
    def callSportsbookAPI(self, event_id, markets):
        """Call sportsbook API to get odds."""
        API_KEY = '4176fcde0a060dfeb152fc085e8ec6f9'

        SPORT = 'soccer_epl' 

        REGIONS = 'uk,us' # uk | us | eu | au. Multiple can be specified if comma delimited

        MARKETS = ','.join(markets)

        ODDS_FORMAT = 'american' # decimal | american

        DATE_FORMAT = 'iso' # iso | unix

        # Event ID comes from get_event_id(), where we call sportsbook API and locate the correct event ID
        # Event ID is necessary in order to get more specific and special market odds
        EVENT_ID = event_id # Example: "5528d0b167ff7ae068b6d0478eb997c7" # Tottenham vs. Luton

        ENDPOINT = f'https://api.the-odds-api.com/v4/sports/{SPORT}/events/{EVENT_ID}/odds'
        
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
        return json.loads(odds_response.text)

        
    def add_question(self, question):
        """Once Questions are built, insert them back into database using banter API."""
        return
        
        
    def track_game_time(self):
        """Ping Sports API (Not Sportsbook) for game time. Separate Thread"""
        return
        
    def question_testing(self, question):
        with open("test_file.json", 'a') as file:
            json.dump(question, file, indent = 4, ensure_ascii=False)
        

game = gameSession(12)
game.build_questions("pregame")