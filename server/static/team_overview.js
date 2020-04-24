const stage_mapping = {
    "0": "Not started",
    "1": "Morning started",
    "2": "At lunch",
    "3": "Afternoon started",
    "4": "Found goal",
    "5": "Rally ended"
};
function get_rally_stage(team_json) {
    if (has_value(team_json), "rally-stage") {
        stage_number = team_json["rally-stage"];
        return stage_mapping[stage_number];
    }
    return "N/A";
}

function build_team_info(team_json) {
    //var s = "<h3>" + get_value(team_json, "team-number") + ": " + get_value(team_json, "team-name") + "</h3>\n";
    var s = "";
    var position = "";
    if (has_value(team_json, "minibus")) {
        var minibus = team_json["minibus"];
        if (has_value(minibus, "current_section")) {
            position += "<tr><td>Section " + minibus["current_section"] + "</td></tr>";
        }
        if (has_value(minibus, "distance")) {
            position += "<tr><td>Distance " + minibus["distance"].toFixed(2) + "</td></tr>";
        }
        if (has_value(minibus, "speed")) {
            position += "<tr><td>Speed " + minibus["speed"].toFixed(2) + "</td></tr>";
        }
        if (has_value(minibus, "seating")) {
            var all_user_ids = new Set();
            var all_users = {};
            if (has_value(team_json, "connected-users")) {
                var connected_users = team_json["connected-users"];
                for (player_index in connected_users) {
                    player = connected_users[player_index];
                    var id = player["id"];
                    all_user_ids.add(id);
                    all_users[id.toString()] = player["name"];
                }
            }

            var seating = minibus["seating"];
            s += "<table border='1'>";
            for (var i = 0; i < 9; i++) {
                if (i % 3 == 0) {
                    s += "<tr>";
                }

                s += "<td>";
                var seat_number = i + 1;
                var anyone = get_value(seating, seat_number.toString(), null);
                if (anyone != null) {
                    var user_id = get_value(anyone, "id");
                    s += "[" + user_id + "] ";
                    s += get_value(anyone, "name");
                    all_user_ids.delete(user_id);
                }
                s += "</td>";

                if (i % 3 == 2) {
                    s += "</tr>";
                }
            }
            if (all_user_ids.size > 0) {
                s += "<tr><td colspan='3'>";
                for (let user_id of all_user_ids) {
                    s += "[" + user_id + "] ";
                    s += all_users[user_id.toString()];
                    s += " ";
                }
                s += "</td></tr>\n";
            }
            s += "</table>";
        }
    }
    s += "Status: " + get_rally_stage(team_json) + "<br>\n";
    if (position.length > 0) {
        s += "<table><tr><td>Position</td><td><table>" + position + "</table></td></tr></table>\n";
    } else {
        s += "Position: Unknown<br>\n";
    }
    s += "<br>\n";
    s += "Start time: " + get_json_date_value(team_json, "start-time") + "<br>\n";
    s += "Lunch time: " + get_json_date_value(team_json, "lunch-time") + "<br>\n";
    s += "Arrived at goal: " + get_json_date_value(team_json, "found-goal-time") + "<br>\n";
    s += "Ended: " + get_json_date_value(team_json, "goal-time") + "<br>\n";
    s += "Latest update: " + get_json_date_value(team_json, "watchdog") + "<br>\n";

    // Rebus overview
    s += "<table border='1'><tr>";
    for (var rebus_number = 1; rebus_number < 9; rebus_number++) {
        var rn_s = rebus_number.toString();
        var normal = "";
        var help = "";
        var solution = "";
        var solved = false;
        var test_count = 0;
        if (has_value(team_json, "rebus-solutions")) {
            rebus_solutions = team_json["rebus-solutions"];
            if (has_value(rebus_solutions, rn_s)) {
                rebus_solution = rebus_solutions[rn_s];
                test_count = parseInt(get_value(rebus_solution, "test_count", "0"));
                solved = get_value(rebus_solution, "solved", false);
            }
        }
        if (has_value(team_json, "rebus-statuses")) {
            rebus_statuses = team_json["rebus-statuses"];
            for (index in rebus_statuses) {
                rebus_status = rebus_statuses[index];
                status_rebus_number = parseInt(get_value(rebus_status, "rebus-number", "0"));
                if (status_rebus_number == rebus_number) {
                    var given = get_value(rebus_status, "given_rebuses", null);
                    normal = get_value(given, "Normal", "");
                    help = get_value(given, "Help", "");
                    solution = get_value(given, "Solution", "");
                }
            }
        }

        var status = "";
        var color = "";
        if (normal.length > 0) {
            status = "N";
            color = solved ? "green" : "cyan";
        }
        if (help.length > 0) {
            status = "H";
            color = solved ? "yellow" : "orange";
        }
        if (solution.length > 0) {
            status = "S";
            color = solved ? "red" : "magenta";
        }
        if (status.length > 0) {
            status += test_count;
        }
        s += "<td style='background-color: " + color + "'>" + status + "</td>";
    }
    s += "</tr></table>";

    return s;
}
