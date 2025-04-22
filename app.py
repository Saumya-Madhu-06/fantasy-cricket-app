from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Dict, Tuple
import itertools

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "FastAPI is working!"}

# Enable CORS for frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAYER_TYPES = ["WK", "BAT", "ALLROUNDER", "BOWLER"]

class Player(BaseModel):
    name: str
    team: str
    type: str
    role: str
    past_runs: List[int]
    past_wickets: List[int]
    head_to_head: Dict[str, Dict[str, int]]
    selection_percent: float
    captain_percent: float
    vice_captain_percent: float

class InputData(BaseModel):
    team1_players: List[Player]
    team2_players: List[Player]
    preferred_conditions: Dict[str, str]

def average(lst):
    return sum(lst) / len(lst) if lst else 0

def score_player(player: Dict, preferred_conditions: Dict) -> float:
    score = 0
    score += average(player["past_runs"]) * 1.0
    score += average(player["past_wickets"]) * 20.0
    score += player["selection_percent"] * 0.1
    score += player["captain_percent"] * 0.2
    score += player["vice_captain_percent"] * 0.15
    if preferred_conditions.get("good_for") == player.get("role"):
        score += 5
    return score

def is_valid_team(team: List[Dict]) -> bool:
    if len(team) != 11:
        return False

    team1_count = sum(1 for p in team if p["team"] == "Team1")
    team2_count = 11 - team1_count
    if team1_count > 10 or team2_count > 10:
        return False

    type_counts = {t: 0 for t in PLAYER_TYPES}
    for p in team:
        type_counts[p["type"]] += 1

    if any(type_counts[t] > 8 or type_counts[t] < 1 for t in PLAYER_TYPES):
        return False

    return True

def generate_valid_teams(all_players: List[Dict]) -> List[List[Dict]]:
    valid_teams = []
    for combo in itertools.combinations(all_players, 11):
        team = list(combo)
        if is_valid_team(team):
            valid_teams.append(team)
    return valid_teams

def assign_roles_and_score(team: List[Dict], preferred_conditions: Dict) -> Tuple[List[Dict], float]:
    for p in team:
        p["score"] = score_player(p, preferred_conditions)

    sorted_team = sorted(team, key=lambda x: x["score"], reverse=True)
    captain = sorted_team[0]
    vice_captain = sorted_team[1]

    total_score = 0
    for p in team:
        multiplier = 1.0
        if p["name"] == captain["name"]:
            multiplier = 2.0
        elif p["name"] == vice_captain["name"]:
            multiplier = 1.5
        total_score += p["score"] * multiplier

    return team, total_score

def get_top_teams(valid_teams: List[List[Dict]], preferred_conditions: Dict, top_n=5) -> Tuple[List[Tuple], List[Tuple]]:
    scored_teams = []
    for team in valid_teams:
        scored_team, score = assign_roles_and_score(team, preferred_conditions)
        scored_teams.append((scored_team, score))

    scored_teams.sort(key=lambda x: x[1], reverse=True)
    return scored_teams[:top_n], scored_teams[-top_n:]

@app.post("/generate-teams")
async def generate_teams(data: InputData):
    all_players = [p.dict() for p in data.team1_players + data.team2_players]
    valid_teams = generate_valid_teams(all_players)
    top_teams, low_teams = get_top_teams(valid_teams, data.preferred_conditions)

    def format_team(team_data):
        team, score = team_data
        return {
            "score": round(score, 2),
            "players": [p["name"] for p in team],
            "captain": team[0]["name"],
            "vice_captain": team[1]["name"]
        }

    return {
        "top_teams": [format_team(t) for t in top_teams],
        "low_teams": [format_team(t) for t in low_teams]
    }
