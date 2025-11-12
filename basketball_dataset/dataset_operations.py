from math import atan2, degrees
import numpy as np
def left_basket(moment):
  """
  This function takes a moment in the game and returns if the ball is in the left basket.
  """
  return (3.5 <= moment['ball_coordinates']['x'] <= 6) and (24 <= moment['ball_coordinates']['y'] <= 26)

def right_basket(moment):
  """
  This function takes a moment in the game and returns if the ball is in the right basket.
  """
  return (88 <= moment['ball_coordinates']['x'] <= 90.5) and (24 <= moment['ball_coordinates']['y'] <= 26)

# using find_actions() criteria from https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=csu14943636475232&disposition=inline
def locate_ballhandler(moment, poss_team_id):
  """
  This function takes a moment in the game as well as the team ID in possession.
  It returns the ID of the presumed ball-handler (player closest to the ball).
  The outline of this function is based on criteria from 'https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=csu14943636475232&disposition=inline'
  """
  import math

  ball_coords = [moment['ball_coordinates']['x'], moment['ball_coordinates']['y']]

  # arbitrarily large distance
  shortest_distance = 10000

  for player in moment['player_coordinates']:
    player_coords = [player['x'], player['y']]
    distance = math.dist(ball_coords, player_coords)

    if (distance < shortest_distance) and (player['teamid'] == poss_team_id):
      shortest_distance = distance
      handler_id = player['playerid']

  if shortest_distance > 5:
    return None

  return handler_id

def locate_defender(moment, poss_team_id, handler_id = None):
  """
  This function takes a moment in the game, the team ID in possession, and the ID of the ball-handler (output of locate_handler).
  It returns the ID of the presumed on-ball defender (defender closest to the ball).
  The outline of this function is based on criteria from 'https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=csu14943636475232&disposition=inline'
  """
  import math

  # if no ball-handler, then there is no on-ball defender
  if handler_id is None:
    return None

  handler_coords = [[d['x'], d['y']] for d in moment['player_coordinates'] if d['playerid'] == handler_id][0]

  # arbitrarily large distance
  shortest_distance = 10000

  for player in moment['player_coordinates']:
    player_coords = [player['x'], player['y']]
    distance = math.dist(handler_coords, player_coords)

    if (distance < shortest_distance) and (player['teamid'] != poss_team_id):
      shortest_distance = distance
      defender_id = player['playerid']

  # if defender > 12 ft away from handler, defender is likely not the on-ball defender
  if shortest_distance > 12:
    return None

  return defender_id

def locate_screener(moment, poss_team_id, handler_id = None, defender_id = None):
  """
  This function takes a moment in the game, the team ID in possession, the ball-handler ID and the on-ball defender ID.
  It returns the ID of the presumed screener (offensive player setting the screen).
  The of this function is based on criteria from 'https://etd.ohiolink.edu/acprod/odb_etd/ws/send_file/send?accession=csu14943636475232&disposition=inline'
  """
  import math

  # if no ball handler, on-ball screen cannot occur
  if handler_id is None:
    return None

  handler_coords = [[d['x'], d['y']] for d in moment['player_coordinates'] if d['playerid'] == handler_id][0]

  # arbitrarily large distance
  shortest_distance = 10000

  screener_id = None
  for player in moment['player_coordinates']:
    player_coords = [player['x'], player['y']]
    distance = math.dist(handler_coords, player_coords)

    if (distance < shortest_distance) and (player['teamid'] == poss_team_id) and (player['playerid'] != handler_id):
      shortest_distance = distance
      screener_id = player['playerid']

  # if no screener, end function
  if screener_id is None:
    return None

  # if w/in distance of 10 ft from basket, not a screen and reject example
  screener_coords = [[d['x'], d['y']] for d in moment['player_coordinates'] if d['playerid'] == screener_id][0]
  basket_coords = [25, 89.25]
  if math.dist(screener_coords, basket_coords) < 10:
    return None

  # if screener > 5ft from handler, not a screen and reject example
  if shortest_distance > 5:
    return None

  # if no defender, no ball screen and reject
  if defender_id is None:
    return None

  defender_coords = [[d['x'], d['y']] for d in moment['player_coordinates'] if d['playerid'] == defender_id][0]

  # if handler and defender not w/in 10 ft, not a ball screen and reject example
  if math.dist(handler_coords, defender_coords) > 10:
    return None

  return screener_id

def find_screen(moment, poss_team_id, handler_id = None, defender_id = None, screener_id = None):
  """
  This function takes a moment in the game, the team ID in possession, and the player ID's of the ball-handler, on-ball defender, and screener.
  It returns a tuple of the form:
    - True if a screen is found, False otherwise
    - The ID of the ball-handler
    - The ID of the on-ball defender
    - The ID of the screener
  """
  import math

  if handler_id and defender_id and screener_id:
    ball_coords = [moment['ball_coordinates']['x'], moment['ball_coordinates']['y']]
    basket_coords = [25, 89.25]
    # check if ball past half-court and not too close to basket
    if (ball_coords[1] > 47) and math.dist(ball_coords, basket_coords) > 10:
      return True, handler_id, defender_id, screener_id
  return False, handler_id, defender_id, screener_id

def filter_candidate_events(events):
  """
  This function takes in a generator of events and outputs a generator that is filtered to only include potential PNR/PNP actions.
  It also modifies the events to be worked with in a uniform format by rotating the coordinates depending on the direction of play.
  There is a bit of hard-coding in the directionality section, which is necessary due to mistimed events in the raw data.
  """
  import math

  filter_events = {1,5} # Going to make this just 5 for turnovers {1,2,5,6}
  start_counter = 0
  game_id = events[0]['gameid']
  for event in events:
    if ((event['event_info']['type'] == 5) and not math.isnan(event['event_info']['possession_team_id']) and event["event_info"]["desc_home"]!="nan" and event["event_info"]["desc_away"]!="nan") or ((event['event_info']['type'] == 1) and not math.isnan(event['event_info']['possession_team_id'])):
      if event['gameid'] != game_id:
        start_counter = 0

      game_id = event['gameid']

      if len(event['moments']) == 0:
        continue

      quarter = event['moments'][0]['quarter']

      if quarter == 1 and start_counter == 0:
        for moment in event['moments']:
          if left_basket(moment):
            first_poss_team_id = event['event_info']['possession_team_id']
            first_direction = 'left'
            second_direction = 'right'
            if game_id in ["0021500292", "0021500648"]:
              first_direction = 'right'
              second_direction = 'left'
            event['event_info']['direction'] = first_direction
            start_counter += 1
            break
          elif right_basket(moment):
            first_poss_team_id = event['event_info']['possession_team_id']
            first_direction = 'right'
            second_direction = 'left'
            if game_id == "0021500648":
              first_direction = 'left'
              second_direction = 'right'
            event['event_info']['direction'] = first_direction
            start_counter += 1
            break
      elif quarter < 3:
        if event['event_info']['possession_team_id'] == first_poss_team_id:
          direction = first_direction
        else:
          direction = second_direction
        event['event_info']['direction'] = direction
      elif quarter >= 3:
        if event['event_info']['possession_team_id'] == first_poss_team_id:
          direction = second_direction
        else:
          direction = first_direction
        event['event_info']['direction'] = direction

      if 'direction' not in event['event_info']:
        continue

      # assign now rotate coordinates based on direction
      if event['event_info']['direction'] == 'left':
        for moment in event['moments']:

          ball_x = moment['ball_coordinates']['y']
          ball_y = 94 - moment['ball_coordinates']['x']
          moment['ball_coordinates']['x'] = ball_x
          moment['ball_coordinates']['y'] = ball_y

          for player_coord in moment['player_coordinates']:
            x = player_coord['y']
            y = 94 - player_coord['x']
            player_coord['x'] = x
            player_coord['y'] = y

      else:
        for moment in event['moments']:

          ball_x = 50 - moment['ball_coordinates']['y']
          ball_y = moment['ball_coordinates']['x']
          moment['ball_coordinates']['x'] = ball_x
          moment['ball_coordinates']['y'] = ball_y

          for player_coord in moment['player_coordinates']:
            x = 50 - player_coord['y']
            y = player_coord['x']
            player_coord['x'] = x
            player_coord['y'] = y
            
      if event['event_info']['direction'] == 'left':
        for moment in event['moments']:
          
          ball_x = 50 - moment['ball_coordinates']['x']
          ball_y = 94 - moment['ball_coordinates']['y']
          moment['ball_coordinates']['x'] = ball_x
          moment['ball_coordinates']['y'] = ball_y

          for player_coord in moment['player_coordinates']:
            x = 50 - player_coord['x']
            y = 94 - player_coord['y']
            player_coord['x'] = x
            player_coord['y'] = y
      
      
      def add_speed_and_direction_unitvec(event, fps=25):
          """
          Adds 'speed', 'dir_x', 'dir_y' (unit direction vector) to each player and the ball
          in each frame of event['moments'].
          Operates in-place on the event dict.
          """
          dt = 1 / fps
          moments = event["moments"]

          for t in range(1, len(moments)):
              prev = moments[t - 1]
              curr = moments[t]

              # --- Ball ---
              bx_prev, by_prev = prev["ball_coordinates"]["x"], prev["ball_coordinates"]["y"]
              bx_curr, by_curr = curr["ball_coordinates"]["x"], curr["ball_coordinates"]["y"]

              dx, dy = bx_curr - bx_prev, by_curr - by_prev
              dist = np.sqrt(dx**2 + dy**2)
              speed = dist / dt
              dir_x = dx / dist if dist != 0 else 0
              dir_y = dy / dist if dist != 0 else 0

              curr["ball_coordinates"]["speed"] = speed
              curr["ball_coordinates"]["dir_x"] = dir_x
              curr["ball_coordinates"]["dir_y"] = dir_y

              # --- Players ---
              prev_coords = {p["playerid"]: (p["x"], p["y"]) for p in prev["player_coordinates"]}
              for p in curr["player_coordinates"]:
                  pid = p["playerid"]
                  if pid in prev_coords:
                      x1, y1 = prev_coords[pid]
                      dx, dy = p["x"] - x1, p["y"] - y1
                      dist = np.sqrt(dx**2 + dy**2)
                      p["speed"] = dist / dt
                      p["dir_x"] = dx / dist if dist != 0 else 0
                      p["dir_y"] = dy / dist if dist != 0 else 0
                  else:
                      p["speed"] = np.nan
                      p["dir_x"] = np.nan
                      p["dir_y"] = np.nan

          # Initialize first frame with NaNs (no prior)
          for p in moments[0]["player_coordinates"]:
              p["speed"] = np.nan
              p["dir_x"] = np.nan
              p["dir_y"] = np.nan
          moments[0]["ball_coordinates"]["speed"] = np.nan
          moments[0]["ball_coordinates"]["dir_x"] = np.nan
          moments[0]["ball_coordinates"]["dir_y"] = np.nan

          return event
      if event['event_info']['type'] == 5:
        event = add_speed_and_direction_unitvec(event)
        handler_has_ball = False
        lost_possession = False
        moments = event["moments"]
        for moment in moments:
          event_team = event["primary_info"]["team_id"]
          event_player = event["primary_info"]["player_id"]

          for player_coord in moment['player_coordinates']:
              if player_coord['playerid'] == event_player:
                handler_x =player_coord["x"]
                handler_y = player_coord["y"]

          ball_x = moment['ball_coordinates']['x']
          ball_y = moment['ball_coordinates']['y']
          ball_spped = moment["ball_coordinates"]["speed"]
          
          if not lost_possession:
            if handler_has_ball == False:
              if np.linalg.norm(np.array([ball_x,ball_y])-np.array([handler_x,handler_y]))<2:
                handler_has_ball = True
            else:
              if np.linalg.norm(np.array([ball_x,ball_y])-np.array([handler_x,handler_y]))>5:
                lost_possession = True
          else:
            if ball_spped<3:
              break
        event["event_info"]["quarter"] = moment["quarter"]
        event["event_info"]["game_clock"] = moment["game_clock"]
        event["event_info"]["shot_clock"] = moment["shot_clock"]
        event["event_info"]["event_moment"] = moment
        event["event_info"]["event_type"] = "turnover"
          
      if event["event_info"]["type"] == 1:
        moments = event["moments"]
        for moment in moments:
          event_team = event["primary_info"]["team_id"]
          event_player = event["primary_info"]["player_id"]
          ball_x = moment['ball_coordinates']['x']
          ball_y = moment['ball_coordinates']['y']
          if np.linalg.norm(np.array([ball_x,ball_y])-np.array([25,89.25])) < 1.5:
            break
        event["event_info"]["quarter"] = moment["quarter"]
        event["event_info"]["game_clock"] = moment["game_clock"]
        event["event_info"]["shot_clock"] = moment["shot_clock"]
        event["event_info"]["event_type"] = "made shot"
      
      event["event_info"]["game_id"] = game_id
        

      # method to find screen situations for potential pnr / pnp for each event
      # event_poss_team_id = event['event_info']['possession_team_id']
      handler_id = None
      defender_id = None
      screener_id = None

      last_clock = 0
      screen_frame_start = None
      frame_id = 0
      screen_frame_count = 0
      num_moments = len(event['moments'])

      # for moment in event['moments']:
        # current_handler = locate_ballhandler(moment, event_poss_team_id)
        # current_defender = locate_defender(moment, event_poss_team_id, current_handler)
        # current_screener = locate_screener(moment, event_poss_team_id, current_handler, current_defender)

        # screen = find_screen(moment, event_poss_team_id, current_handler, current_defender, current_screener)

        # current_clock = moment['game_clock']

      #   if screen[0] == True and current_clock != last_clock:
      #     if screen_frame_count == 0:
      #       screen_frame_start = frame_id
      #       screen_frame_count += 1
      #       screen_time_stamp_start = moment['game_clock']

      #       handler_id = current_handler
      #       defender_id = current_defender
      #       screener_id = current_screener

      #     elif screen[1] == handler_id and screen[2] == defender_id and screen[3] == screener_id:
      #       screen_frame_count += 1

      #       handler_id = screen[1]
      #       defender_id = screen[2]
      #       screener_id = screen[3]

      #   elif screen[0] == False and screen_frame_count > 8 and current_clock != last_clock:
      #     event['event_info']['screen_potential'] = True
      #     event['event_info']['handler_id'] = handler_id
      #     event['event_info']['defender_id'] = defender_id
      #     event['event_info']['screener_id'] = screener_id
      #     event['event_info']['screen_frame_start'] = screen_frame_start
      #     event['event_info']['screen_frame_end'] = frame_id
      #     event['event_info']['screen_time_stamps'] = [round(screen_time_stamp_start, 2), round(moment['game_clock'])]
      #     screen_frame_count = 0
      #     break
      #   else:
      #     screen_frame_count = 0

      #   frame_id += 1
      #   last_clock = current_clock
      #   if frame_id == num_moments:
      #     event['event_info']['screen_potential'] = False
      #     event['event_info']['handler_id'] = handler_id
      #     event['event_info']['defender_id'] = defender_id
      #     event['event_info']['screener_id'] = screener_id
      #     event['event_info']['screen_frame_start'] = screen_frame_start
      #     event['event_info']['screen_frame_end'] = frame_id
      #     event['event_info']['screen_time_stamps'] = [0, 0]
      #     screen_frame_count = 0
      #     break

      # if event['event_info']['screen_potential'] == True:
      yield event