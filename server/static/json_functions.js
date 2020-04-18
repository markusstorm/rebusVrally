function get_value(json_obj, property, def) {
    if (def === undefined) def = "";
    if (json_obj == null) return def;
    if (json_obj.hasOwnProperty(property)) {
        return json_obj[property];
    }
    return def;
}

function has_value(json_obj, property) {
    if (json_obj == null) return false;
    if (json_obj.hasOwnProperty(property)) {
        return true;
    }
    return false;
}

function get_json_date_value(json_obj, property) {
    if (has_value(json_obj, property)) {
        val = json_obj[property];
        if (val != null) {
            return val;
        }
    }
    return "-";
}
