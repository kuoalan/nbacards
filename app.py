import os
import requests
from flask import Flask, render_template, json, request, session, url_for
import plotly.graph_objs as graph_obj

app = Flask(__name__)

# Locate required file, get secret keys
player_id_file = os.path.join(app.static_folder, 'player_ids.json')
sessions_key = os.environ.get('sessions_key', None)
yt_api_key = os.environ.get('yt_secret_key', None)
port = int(os.environ.get("PORT", 5000))

app.secret_key = 'playball'

# Load player ID file
with open(player_id_file) as f:
    player_ids = json.load(f)

# Set up array of player names
player_names = []
for player in player_ids:
    player_names.append(player)
player_names.sort()

stat_cats = ['pts','reb','ast','stl','blk','turnover', 'fg_pct', 'fg3_pct', 'ft_pct', 'fga', 'fg3a', 'fta','fgm','fg3m','ftm']


def get_max_stats(player_id_list):
    """
    Calculates season stat leaders for each counting and shooting percentage stat. Uses
    :param: player_id_list: A list containing the player ids of each active player.
    :return: dict: a dictionary containing the highest statistic or percentage for each statistical category for the current season
    """
    ids_list = []
    for each_player in player_id_list:
        ids_list.append(player_id_list[each_player][1])
    ids_list_str = ','.join(str(i) for i in ids_list)
    # Currently in offseason, changed to 2020 season stats. Get data from balldontlie API.
    max_stats_req = requests.get(f'https://www.balldontlie.io/api/v1/season_averages?season=2020&player_ids[]={ids_list_str}')
    max_stats_data = max_stats_req.json()
    # Set up dictionary to hold max stats
    max_stats = {key: None for key in stat_cats}
    for key in max_stats:
        if key in ['fga','fg3a','fta']:
            cur_max = max_stats_data['data'][0][key] * max_stats_data['data'][0]['games_played']
        else:
            # Minimum of 20 games played to qualify
            if max_stats_data['data'][0]['games_played'] < 20:
                cur_max = 0
            # Minimum of 1 FGA/3PTA/FTA to qualify for each shooting percentage stat
            elif key == 'fg_pct':
                if max_stats_data['data'][0]['fga'] < 1:
                    cur_max = 0
            elif key == 'fg3_pct':
                if max_stats_data['data'][0]['fg3a'] < 1:
                    cur_max = 0
            elif key == 'ft_pct':
                if max_stats_data['data'][0]['fta'] < 1:
                    cur_max = 0
            else:
                cur_max = max_stats_data['data'][0][key]
        for i in range(1,len(max_stats_data['data'])):
            if key in ['fga','fg3a','fta']:
                cur_max = max(cur_max, max_stats_data['data'][i][key] * max_stats_data['data'][i]['games_played'])
            elif max_stats_data['data'][i]['games_played'] < 20:
                pass
            elif key == 'fg_pct':
                if max_stats_data['data'][i]['fga'] > 5:
                    cur_max = max(cur_max, max_stats_data['data'][i][key])
            elif key == 'fg3_pct':
                if max_stats_data['data'][i]['fg3a'] > 3:
                    cur_max = max(cur_max, max_stats_data['data'][i][key])
            elif key == 'ft_pct':
                if max_stats_data['data'][i]['fta'] > 3:
                    cur_max = max(cur_max, max_stats_data['data'][i][key])
            else:
                if max_stats_data['data'][i]['games_played'] > 10:
                    cur_max = max(cur_max, max_stats_data['data'][i][key])
        max_stats[key] = cur_max
    return max_stats


def create_graph(percents, categories, player_id, graph_type):
    """
    Function that creates a radial graph for displaying how the specified player's stats compare to the league leader

    :param percents: list containing percentages for each counting & shooting stat (player stat / league leader stat)
    :param categories: list containing statistical categories to be included in the graph
    :param player_id: integer corresponding to the balldontlie player ID
    :param graph_type: string corresponding to the type of graph (used to name file when saving image)

    :return: No explicit return, saves an image file containing the graph
    """
    fig = graph_obj.Figure(data=graph_obj.Scatterpolar(
        r = percents,
        theta=categories,
        fill='toself'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True
            ),
        ),
        showlegend=False,
        font=dict(
            family="Segoe UI",
            size=32
        )
    )
    fig.update_polars(radialaxis_showticklabels=False, radialaxis_showline=False, radialaxis_range=[0, 100])
    fig.write_image(f'static/stats_plot_{player_id}_{graph_type}.png')


def create_shot_graph(attempt_perc,made_perc,player_id):
    """
    Function that creates a graph showing made shots overlaid on attempted shots
    :param attempt_perc: list containing attempt percentages for each shooting stat (player attempts / league leader attempts)
    :param made_perc: list containing make percentages for each shooting stat (player makes / league leader makes)
    :param player_id: integer corresponding to player's balldontlie ID

    :return: No explicit return, saves image file contaiing the graph
    """
    categories = ['FG','3PT', 'FT','FG']

    fig = graph_obj.Figure()
    # Plot attempts line and fill
    fig.add_trace(graph_obj.Scatterpolar(
        r=attempt_perc,
        theta=categories,
        fill='toself',
        name='Attempts',
        line = dict(color="#bee2f7")
    ))
    # Plot makes line and fill
    fig.add_trace(graph_obj.Scatterpolar(
        r=made_perc,
        theta=categories,
        fill='toself',
        name='Makes',
        line=dict(color="#78e38a")
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True
            )),
        showlegend=False,
        font=dict(
            family="Segoe UI",
            size=32
        )
    )
    fig.update_polars(radialaxis_showticklabels=False, radialaxis_showline=False, radialaxis_range=[0, 100])
    fig.write_image(f'static/shot_plot_{player_id}.png')


# Route for initial page load
@app.route('/')
def index():
    # Save max stats on initial page load and save in session data
    session['max_stats'] = get_max_stats(player_ids)
    return render_template('index.html', show_stats = False, player_list = player_names)


# Route for getting player stats
@app.route('/', methods=['POST'])
def submit():
    search_target = request.form['player_name']
    max_stats_dict = session['max_stats']
    # Search through players for matching name (case insensitive)
    for player in player_ids:
        if search_target.lower() in player.lower():
            bdl_id = player_ids[player][1]
            # Get player data (height, weight, position, etc)
            player_info_req = requests.get(f'https://www.balldontlie.io/api/v1/players/{bdl_id}')
            # Get season statistics (set to 2020 season because it is currently the offseason)
            player_stats_req = requests.get(
                f'https://www.balldontlie.io/api/v1/season_averages?season=2020&player_ids[]={bdl_id}')
            player_stats = player_stats_req.json()
            player_info = player_info_req.json()
            if len(player_stats['data']) == 0:
                continue
            # Extract player information from response
            position_short = player_info['position']
            position_array = position_short.split('-')
            # Replace abbreviation with full position names
            for ind, item in enumerate(position_array):
                if item == 'C':
                    position_array[ind] = 'Center'
                elif item == 'F':
                    position_array[ind] = 'Forward'
                elif item == 'G':
                    position_array[ind] = 'Guard'
            position = '-'.join(position_array)
            height_feet = player_info['height_feet']
            height_inches = player_info['height_inches']
            weight = player_info['weight_pounds']
            team = player_info['team']['full_name']
            # Extract counting stats from response
            stat_source = player_stats['data'][0]
            stat_perc_array = []
            stat_graph_cats = ['pts', 'reb', 'ast', 'stl', 'blk', 'turnover','pts']
            for cat in stat_graph_cats:
                stat_data = stat_source[cat]
                stat_perc = stat_data/max_stats_dict[cat]*100
                stat_perc_array.append(stat_perc)
            create_graph(stat_perc_array, ['Points','Rebounds','Assists', 'Steals','Blocks','Turnovers','Points'], bdl_id, 'stats')
            stat_plot_url = f'static/stats_plot_{bdl_id}_stats.png'
            # Extract shooting %'s from response
            shooting_perc_array = []
            shooting_graph_cats = ['fg_pct', 'fg3_pct', 'ft_pct','fga','fg3a','fta','fg_pct']
            for cat in shooting_graph_cats:
                shooting_data = stat_source[cat]
                if cat in ['fga','fg3a','fta']:
                    shooting_perc = shooting_data*stat_source['games_played'] / max_stats_dict[cat] * 100
                else:
                    shooting_perc = shooting_data/max_stats_dict[cat] * 100
                shooting_perc_array.append(shooting_perc)
            create_graph(shooting_perc_array, ['FG%', '3PT%', 'FT%','FGA','3PTA','FTA','FG%'], bdl_id, "shooting")
            shooting_plot_url = f'static/stats_plot_{bdl_id}_shooting.png'
            # Extract shot attempts and makes from response
            attempts_array =[]
            makes_array = []
            shot_cats = {'fga':'fg_pct','fg3a':'fg3_pct','fta':'ft_pct','fga':'fg_pct'}
            # Get percentage (player stat / league leader stat) for each shooting category
            for key,value in shot_cats.items():
                attempts_data = stat_source[key] * stat_source['games_played']
                attempts_perc = attempts_data/max_stats_dict[key]*100
                attempts_array.append(attempts_perc)
                makes_perc = (stat_source[value] * attempts_perc)
                makes_array.append(makes_perc)
            # Create graph of makes & attempts
            create_shot_graph(attempts_array,makes_array,bdl_id)
            shot_graph_url = f'static/shot_plot_{bdl_id}.png'
            # Get counting stats
            ppg = stat_source['pts']
            rebounds = stat_source['reb']
            assists = stat_source['ast']
            steals = stat_source['stl']
            blocks = stat_source['blk']
            turnovers = stat_source['turnover']
            fga = stat_source['fga']
            fta = stat_source['fta']
            # Calculate true shooting percentage
            fg_pct = round(stat_source['fg_pct'] * 100, 2)
            fg3_pct = round(stat_source['fg3_pct'] * 100, 2)
            ft_pct = round(stat_source['ft_pct'] * 100, 2)
            ts = round((ppg / (2 * (fga + 0.44 * fta))) * 100, 2)
            # Get image from basketball reference
            bbref_id = player_ids[player][0]
            imageurl = 'https://www.basketball-reference.com/req/202105076/images/players/' + bbref_id + ".jpg"
            yt_query = requests.get(
                f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=20&q={player} 2020 nba highlights&type=video&key={yt_api_key}')
            yt_result = yt_query.json()
            if "error" in yt_result:
                yt_vid_id = False
            else:
                yt_vid_id = yt_result['items'][0]['id']['videoId']
            return render_template('index.html', name=player, position=position, points=ppg, rebounds=rebounds,
                                   assists=assists, steals = steals, blocks = blocks, turnovers = turnovers,
                                   fg_pct = fg_pct, fg3_pct = fg3_pct, ft_pct = ft_pct, ts = ts,
                                   height_feet = height_feet, height_inches = height_inches,weight = weight, team = team,
                                   show_stats=True, imageurl = imageurl, player_list = player_names, yt_vid_id = yt_vid_id,
                                   stat_plot_url=stat_plot_url, shooting_plot_url=shooting_plot_url, shot_graph_url=shot_graph_url)
    else:
        error_message = "Data not found!"
        return render_template('index.html', error_message = error_message, player_list = player_names)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
