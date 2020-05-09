import datetime
import json
import os

logged_in_teams = {}
goal_teams = {}

path = "f:/Coding/vt2020_virtuellt_rebusrally/!demo_rallyt_backuper/"
date_dirs = [os.path.join(path, o) for o in os.listdir(path) if os.path.isdir(os.path.join(path,o))]

print(date_dirs)
for date_dir in date_dirs:
    team_dirs = [os.path.join(date_dir, o) for o in os.listdir(date_dir) if os.path.isdir(os.path.join(date_dir,o))]
    for team_dir in team_dirs:
        team_number_str = os.path.basename(team_dir)
        team_number = int(team_number_str)
        team_backups = sorted([os.path.join(team_dir, o) for o in os.listdir(team_dir) if (os.path.isfile(os.path.join(team_dir,o)) and o.endswith(".srb"))])
        if len(team_backups) > 0:
            if team_number not in logged_in_teams:
                logged_in_teams[team_number] = []
            logged_in_teams[team_number].append(os.path.basename(date_dir)) #The date
            restore_file = team_backups[-1]
            try:
                #with open(restore_file, 'r', encoding="utf-8") as f:
                with open(restore_file, 'r') as f:
                    try:
                        content = f.read()
                    except IOError as e:
                        print("Unable to read the old team server state: {0}".format(e))

                    try:
                        _json = json.loads(content, strict=False)
                        #print(_json)
                        if "found-goal-time" in _json:
                            goal_time_str = _json["found-goal-time"]
                            if goal_time_str is not None:
                                goal_time = datetime.datetime.strptime(goal_time_str, "%Y-%m-%d %H:%M:%S")
                                if team_number not in goal_teams:
                                    goal_teams[team_number] = []
                                goal_teams[team_number].append(goal_time)
                    except Exception as e:
                        print("Unable to convert the old state to json: {0}".format(e))
            except IOError as e:
                print("Unable to read the old team server state: {0}".format(e))


print(logged_in_teams)
print(goal_teams)


print("")
print("Logged in teams:")
for team_number in range(-2, 23):
    count = 0
    if team_number in logged_in_teams:
        count = len(logged_in_teams[team_number])
    #if count == 0:
    print("  {0}: {1}".format(team_number, count))

print("Found goal:")
for team_number in range(-2, 23):
    count = 0
    if team_number in goal_teams:
        count = len(goal_teams[team_number])
    #if count == 0:
    print("  {0}: {1}".format(team_number, count))
