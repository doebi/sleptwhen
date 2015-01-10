#!/usr/bin/env python3
import re
import sys
from datetime import datetime, timedelta

#colors
foreground_color = 251
heading_color = 208
heading_line_color = 246
time_color = 231
time_text_color = 246
histogram_color = [ 57, 56, 126, 197 ]
histogram_color_grid = [ 99, 97, 169, 204 ]
weekday_color = 245
weekend_color = 231
bar_color = 28
bar_weekend_color = 82
bar_color_grid = 77
bar_weekend_color_grid = 156
night_color = 51
sunrise_color = 228
noon_color = 226
sunset_color = 214
grid_color = 238

# some static variables
line_pattern = re.compile("sleep\s+\w{3}\s+([\d\w\s:]{20})\s+-\s+\w{3}\s+([\d\w\s:]{20})")
time_format = "%b %d %H:%M:%S %Y"
datafile = "sleeping.data"
day = timedelta(days = 1)
half_hour = timedelta(minutes = 30)
half_hours_in_day = round(day / half_hour)
use_escape_sequences = sys.stdout.isatty()
output_width = 61

# function for parsing single lines of input
def parse_line(line):
    result = line_pattern.match(line)
    if result is None:
        if not line.startswith('#'):
            print("Warning: Pattern didn't match on line. Typo?")
        return None
    else:
        from_time = datetime.strptime(result.group(1), time_format)
        to_time   = datetime.strptime(result.group(2), time_format)
        return { "from" : from_time, "to" : to_time }


def time_overlap(time_span_1, time_span_2):
    if max(time_span_1["from"], time_span_2["from"]) >= \
       min(time_span_1["to"], time_span_2["to"]):
           return timedelta()
    return min(time_span_1["to"], time_span_2["to"]) - \
           max(time_span_1["from"], time_span_2["from"])


def style_text(text, fgcolor = foreground_color, bgcolor = None, bold = False):
    return get_escape_sequence(fgcolor, bgcolor, bold) + text + \
           get_escape_sequence(fgcolor = foreground_color)

def get_escape_sequence(fgcolor = None, bgcolor = None, bold = False):
    if use_escape_sequences:
        return get_reset_sequence() + \
               "\033[%s%s%sm" % \
               ("" if fgcolor is None else ("38;5;%d" % fgcolor), \
               "" if bgcolor is None else (";48;5;%d" % bgcolor), \
               ";1" if bold else "")
        return ""

def get_reset_sequence():
    if use_escape_sequences:
        return "\033[0m"
    return ""

def format_delta(delta):
    fields = get_delta_fields(delta)
    return style_text("%4d" % fields["hours"], fgcolor = time_color) + \
           style_text(" hours ", fgcolor = time_text_color) + \
           style_text("%2d" % fields["minutes"], fgcolor = time_color) + \
           style_text(" minutes", fgcolor = time_text_color)

def get_delta_fields(delta):
    fields = {}
    fields["hours"], remainder = divmod(round(delta.total_seconds()), 3600)
    fields["minutes"], fields["seconds"] = divmod(remainder, 60)
    return fields

def format_heading(heading):
    padded_heading = " " + heading + " "
    heading_pos = int((output_width - len(padded_heading)) / 2)
    full_heading = style_text("┌" + ("─" * heading_pos), fgcolor = heading_line_color) + \
                   style_text(padded_heading, fgcolor = heading_color)
    full_heading += style_text(("─" * (output_width - heading_pos - len(padded_heading))) + "┐", \
                    fgcolor = heading_line_color)
    return full_heading

def format_delta_short(delta):
    fields = get_delta_fields(delta)
    if fields["hours"] == 0 and fields["minutes"] == 0:
        return ""
    if fields["hours"] == 0:
        return style_text("  :", fgcolor = time_text_color) + \
               style_text("%02d" % fields["minutes"], fgcolor = time_color)
    return style_text("%2d" % fields["hours"], fgcolor = time_color) + \
           style_text(":", fgcolor = time_text_color) + \
           style_text("%02d" % fields["minutes"], fgcolor = time_color)


# reading the datafile
with open(datafile, "r") as f:
    lines = f.readlines()

time_spans = []

for l in lines:
    result = parse_line(l)
    if result is not None:
        time_spans.append(result)

if not time_spans:
    sys.exit("Error: Found no parsable data in %s" % datafile)

# computation

latest_time   = time_spans[0]["to"]
earliest_time = time_spans[-1]["from"]

latest_time   = latest_time.replace(hour = 0, minute = 0, second = 0) + day
earliest_time = earliest_time.replace(hour = 0, minute = 0, second = 0)


time_slots = []
aggregated_time_slots = [ timedelta() ] * half_hours_in_day
total_time = timedelta()

current_time = latest_time
while current_time > earliest_time:
    current_time -= half_hour
    time_slot = { "from" : current_time, "to" : current_time + half_hour }
    time_in_slot = timedelta()
    for time_span in time_spans:
        time_in_slot += time_overlap(time_slot, time_span)
    time_slots.append({ "time" : current_time, "time_in_slot" : time_in_slot })
    half_hour_index = current_time.hour * 2 + (1 if current_time.minute >= 30 else 0)
    aggregated_time_slots[half_hour_index] += time_in_slot
    total_time += time_in_slot

time_slots.reverse()

time_header = "       0:00 " + style_text("☾", fgcolor = night_color) + \
              "      6:00 " + style_text("☀", fgcolor = sunrise_color) + \
              "     12:00 " + style_text("☀", fgcolor = noon_color) + \
              "     18:00 " + style_text("☀", fgcolor = sunset_color) + \
              "     24:00 " + style_text("☽", fgcolor = night_color)

grid_header = style_text("▆           ▆           ▆           ▆           ▆", fgcolor = grid_color)
grid_footer = style_text("▀           ▀           ▀           ▀           ▀", fgcolor = grid_color)

level_characters = [ " ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█" ]

print(get_escape_sequence(fgcolor = foreground_color), end = "")

### Print summary
number_of_days = (latest_time - earliest_time).days

print(style_text("Period:  ", bold = True) + \
      earliest_time.strftime("%B %d %Y") + " – " + \
      (latest_time - day).strftime("%B %d %Y") + \
      " (" + \
      style_text("%d" % number_of_days, fgcolor = time_color) + \
      style_text(" days", fgcolor = time_text_color) + ")")

print()

print(style_text("Total time sleeping: ", bold = True) + format_delta(total_time))
print(style_text("Daily average:      ", bold = True) + format_delta(total_time / number_of_days))

print()
print()

### Print histogram
print(style_text("Histogram:", bold = True))
print()
print(time_header)
print("   max  " + grid_header)

number_of_lines = 4

levels = len(level_characters) - 1

min_level = (min(aggregated_time_slots) / number_of_days) / half_hour
max_level = (max(aggregated_time_slots) / number_of_days) / half_hour

def format_histogram_line(label, index):
    line = label + "  "
    slot_index = 0
    for time_slot in aggregated_time_slots:
        level = (time_slot / number_of_days) / half_hour
        # Normalize level to increase resolution
        level = (level - min_level) / (max_level - min_level)
        level = round(level * (levels * number_of_lines)) - (index * levels)
        # Clamp level to permissible range
        level = max(0, min(levels, level))
        grid = slot_index % 12 == 0
        slot_index += 1
        line += style_text(level_characters[level], \
                fgcolor = histogram_color_grid[index] if grid else histogram_color[index],
                bgcolor = grid_color if grid else None)
    line += style_text(" ", bgcolor = grid_color)
    return line

print(format_histogram_line("      ", 3))
print(format_histogram_line("      ", 2))
print(format_histogram_line("      ", 1))
print(format_histogram_line("   min", 0))

print("        " + grid_footer)

print()


### Print month views
current_time = latest_time

# 0 is not a valid month index, so the "month changed" condition
# will always be fulfilled in the first iteration
current_month = 0

# Do not use full block character here to keep separation between lines
levels = len(level_characters) - 2

while current_time > earliest_time:
    current_time -= day

    month_changed = current_time.month != current_month

    if month_changed:
        current_month = current_time.month
        print()
        print()
        print(format_heading(current_time.strftime("%B %Y")))
        print()
        print(time_header)
        print("        " + grid_header)

    weekend = current_time.weekday() in [5, 6]
    sunday  = current_time.weekday() == 6

    time_text = style_text(current_time.strftime("%a"), \
                           fgcolor = weekend_color if weekend else weekday_color, \
                           bold = sunday)
    time_text += current_time.strftime(" %d").replace(" 0", "  ")

    output_line = time_text + "  "

    time_sum = timedelta()

    bar_text = ""

    slot_index = 0

    ### Build chart for day
    for time_slot in time_slots:
        if time_slot["time"] >= current_time and time_slot["time"] < current_time + day:
            time_sum += time_slot["time_in_slot"]
            level = round((time_slot["time_in_slot"] / half_hour) * levels)
            grid = slot_index % 12 == 0
            slot_index += 1
            bar_text += style_text(level_characters[level], \
                        fgcolor = (bar_weekend_color_grid if grid else bar_weekend_color) if weekend \
                        else (bar_color_grid if grid else bar_color),
                        bgcolor = grid_color if grid else None)

    output_line += bar_text

    output_line += style_text(" ", bgcolor = grid_color)

    output_line += " " + format_delta_short(time_sum)

    print(output_line)

    if (current_time.day == 1) or \
       (current_time <= earliest_time):
           # End of month
           print("        " + grid_footer)


# Reset text attributes
print(get_reset_sequence(), end = "")
