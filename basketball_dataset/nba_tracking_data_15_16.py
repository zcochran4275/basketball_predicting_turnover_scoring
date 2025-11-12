# Copyright 2020 The HuggingFace Datasets Authors and the current dataset script contributor.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This is tracking data of the 2015-2016 NBA season"""

import csv
import json
import os
import py7zr
import re

import datasets
import requests
import random

import pandas as pd


_CITATION = """\
@misc{Linou2016,
title = {NBA-Player-Movements},
author={Kostya Linou},
publisher={SportVU},
year={2016}
"""


_DESCRIPTION = """\
This dataset is designed to give further easy access to tracking data.
By merging all .7z files into one large .json file, access is easier to retrieve all information at once.
"""

_HOMEPAGE = "https://github.com/linouk23/NBA-Player-Movements/tree/master/"
_URL = "https://github.com/linouk23/NBA-Player-Movements/raw/master/data/2016.NBA.Raw.SportVU.Game.Logs"
_PBP_URL = "https://github.com/sumitrodatta/nba-alt-awards/raw/main/Historical/PBP%20Data/2015-16_pbp.csv"

res = requests.get(_URL)
text = res.text

json_pattern = r'{"items":*\[.*?\]'
json_match = re.findall(json_pattern, text, re.DOTALL)

ITEMS = json.loads(json_match[0]+"}")['items']

def home_away_event_conversion(number):
    if pd.isna(number.item()):
        return None
    if int(number.item()) == 4:
        return "home"
    elif int(number.item()) == 5:
        return "away"
    else:
        return None
        
def identify_offense(row):
    identified_offense_events = [1, 2, 3, 4, 5]
    if int(row['EVENTMSGTYPE'].item()) in identified_offense_events:
        poss_team_id = row['PLAYER1_TEAM_ID'].item()
    elif ("OFF.FOUL" in str(row["HOMEDESCRIPTION"].item())) or ("OFF.FOUL" in str(row["VISITORDESCRIPTION"].item())):
        poss_team_id = row['PLAYER1_TEAM_ID'].item()
    elif int(row['EVENTMSGTYPE'].item()) == 6:
        poss_team_id = row['PLAYER2_TEAM_ID'].item()
    else:
        poss_team_id = None
    return poss_team_id

class NbaTrackingConfig(datasets.BuilderConfig):
    """BuilderConfig for NbaTracking"""

    def __init__(self, samples, **kwargs):
        super().__init__(**kwargs)
        self.samples = samples

class NbaTracking(datasets.GeneratorBasedBuilder):
    """Tracking data for all games of 2015-2016 season in forms of coordinates for players and ball at each moment."""

    items = ITEMS
    _PBP_URL = _PBP_URL
    
    BUILDER_CONFIG_CLASS = NbaTrackingConfig

    BUILDER_CONFIGS = [
        NbaTrackingConfig(
            name = "tiny",
            samples = 5
        ),
        NbaTrackingConfig(
            name = "small",
            samples = 25
        ),
        NbaTrackingConfig(
            name = "medium",
            samples = 100
        ),
        NbaTrackingConfig(
            name = "full",
            samples = len(items)
        )
    ]
    
    def _info(self):
        features = datasets.Features(
            {    
                "gameid": datasets.Value("string"),
                "gamedate": datasets.Value("string"),
                "event_info": {"id": datasets.Value("string"),
                               "type": datasets.Value("int64"),
                               "possession_team_id": datasets.Value("float64"),
                               "desc_home": datasets.Value("string"),
                               "desc_away": datasets.Value("string")
                              },
                "primary_info": {"team": datasets.Value("string"),
                                 "player_id": datasets.Value("float64"),
                                 "team_id": datasets.Value("float64")
                                },
                "secondary_info": {"team": datasets.Value("string"),
                                   "player_id": datasets.Value("float64"),
                                   "team_id": datasets.Value("float64")
                                  },
                "visitor": {
                    "name": datasets.Value("string"),
                    "teamid": datasets.Value("int64"),
                    "abbreviation": datasets.Value("string"),
                    "players": [
                        {
                        "lastname": datasets.Value("string"),
                        "firstname": datasets.Value("string"),
                        "playerid": datasets.Value("int64"),
                        "jersey": datasets.Value("string"),
                        "position": datasets.Value("string")
                        }
                    ]
                },
                "home": {
                    "name": datasets.Value("string"),
                    "teamid": datasets.Value("int64"),
                    "abbreviation": datasets.Value("string"),
                    "players": [
                        {
                        "lastname": datasets.Value("string"),
                        "firstname": datasets.Value("string"),
                        "playerid": datasets.Value("int64"),
                        "jersey": datasets.Value("string"),
                        "position": datasets.Value("string")
                        }
                    ]
                },
                "moments": [
                    {
                        "quarter": datasets.Value("int64"),
                        "game_clock": datasets.Value("float64"),
                        "shot_clock": datasets.Value("float64"),
                        "ball_coordinates": {
                            "x": datasets.Value("float64"),
                            "y": datasets.Value("float64"),
                            "z": datasets.Value("float64")
                        },
                        "player_coordinates": [
                            {
                                "teamid": datasets.Value("int32"),
                                "playerid": datasets.Value("int32"),
                                "x": datasets.Value("float64"),
                                "y": datasets.Value("float64"),
                                "z": datasets.Value("float64")
                            }
                        ]
                    }
                ]
            }
        )
        
        return datasets.DatasetInfo(
            # This is the description that will appear on the datasets page.
            description=_DESCRIPTION,
            # This defines the different columns of the dataset and their types
            features=features,  # Here we define them above because they are different between the two configurations
            # If there's a common (input, target) tuple from the features, uncomment supervised_keys line below and
            # specify them. They'll be used if as_supervised=True in builder.as_dataset.
            # supervised_keys=("sentence", "label"),
            # Homepage of the dataset for documentation
            homepage=_HOMEPAGE,
            # Citation for the dataset
            citation=_CITATION,
        )

    def _split_generators(self, dl_manager):
        random.seed(9)
        items = random.sample(self.items, self.config.samples)
        
        _URLS = {}
        for game in items:
          name = game['name'][:-3]
          _URLS[name] = _URL + "/" + name + ".7z"
            
        urls = _URLS
        
        data_dir = dl_manager.download_and_extract(urls)
        
        all_file_paths = {}
        for key, directory_path in data_dir.items():
            all_file_paths[key] = os.path.join(directory_path, os.listdir(directory_path)[0])
            
        return [
            datasets.SplitGenerator(
                name=datasets.Split.TRAIN,
                # These kwargs will be passed to _generate_examples
                gen_kwargs={
                    "filepaths": all_file_paths,
                    "split": "train",
                }
            )
        ]

   
    def _generate_examples(self, filepaths, split):
        pbp_out = datasets.DownloadManager().download_and_extract(_PBP_URL)
        pbp = pd.read_csv(pbp_out)
        
        moment_id = 0
        
        for game_title, link in filepaths.items():
            with open(link, encoding="utf-8") as fp:
                game = json.load(fp)
                game_id = game["gameid"]
                game_date = game["gamedate"] 

                for event in game["events"]:
                    event_id = event["eventId"]

                    event_row = pbp.loc[(pbp.GAME_ID == int(game_id)) & (pbp.EVENTNUM == int(event_id))]
                    if len(event_row) != 1:
                        continue

                    event_type = event_row["EVENTMSGTYPE"].item()
                    
                    event_home_desc = event_row["HOMEDESCRIPTION"].item()
                    
                    event_away_desc = event_row["VISITORDESCRIPTION"].item()
                    
                    primary_home_away = home_away_event_conversion(event_row["PERSON1TYPE"])
                    primary_player_id = event_row["PLAYER1_ID"].item()
                    primary_team_id = event_row["PLAYER1_TEAM_ID"].item()
                    
                    secondary_home_away = home_away_event_conversion(event_row["PERSON2TYPE"])
                    secondary_player_id = event_row["PLAYER2_ID"].item()
                    secondary_team_id = event_row["PLAYER2_TEAM_ID"].item()
                    
                    poss_team_id = identify_offense(event_row)
                    
                    visitor_name = event['visitor']['name']
                    visitor_team_id = event['visitor']['teamid']
                    visitor_abbrev = event['visitor']['abbreviation']
                    visitor_players = event['visitor']['players']

                    home_name = event['home']['name']
                    home_team_id = event['home']['teamid']
                    home_abbrev = event['home']['abbreviation']
                    home_players = event['home']['players']

                    moments = [
                        {
                            "quarter": moment[0],
                            "game_clock": moment[2],
                            "shot_clock": moment[3],
                            "ball_coordinates": {
                                "x": moment[5][0][2],
                                "y": moment[5][0][3],
                                "z": moment[5][0][4]
                            },
                            "player_coordinates": [
                                {
                                    "teamid": i[0], 
                                    "playerid": i[1], 
                                    "x": i[2], 
                                    "y": i[3], 
                                    "z": i[4]
                                } for i in moment[5][1:]
                            ]
                        } for moment in event["moments"]
                    ]

                    moment_id += 1
                                
                    yield moment_id, {
                        "gameid": game_id,
                        "gamedate": game_date,
                        "event_info": {
                            "id": event_id,
                            "type": event_type,
                            "possession_team_id": poss_team_id,
                            "desc_home": event_home_desc,
                            "desc_away": event_away_desc
                        },
                        "primary_info": {
                            "team": primary_home_away,
                            "player_id": primary_player_id,
                            "team_id": primary_team_id
                                },
                        "secondary_info": {
                            "team": secondary_home_away,
                            "player_id": secondary_player_id,
                            "team_id": secondary_team_id
                        },
                        "visitor": {
                            "name": visitor_name,
                            "teamid": visitor_team_id,
                            "abbreviation": visitor_abbrev,
                            "players": visitor_players
                        },
                        "home": {
                            "name": home_name,
                            "teamid": home_team_id,
                            "abbreviation": home_abbrev,
                            "players": home_players
                        },
                        "moments": moments
                    }