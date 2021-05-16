import os
import requests
from flask import Flask, render_template, json, request


app = Flask(__name__)

data_file = os.path.join(app.static_folder, 'data.json')
name_id_file = os.path.join(app.static_folder, 'player_dict.json')

yt_api_key = os.environ.get('yt_secret_key', None)

port = int(os.environ.get("PORT", 5000))

with open(data_file) as f:
    player_data = json.load(f)

with open(name_id_file) as f:
    player_name_id = json.load(f)


@app.route('/')
def index():
    return render_template('index.html', show_stats = False, player_list = player_name_id)


@app.route('/', methods=['POST'])
def submit():
    search_target = request.form['player_name']
    for player in player_data['data']:
        full_name = (player['first_name'] + " " + player['last_name'])
        if search_target.lower() in full_name.lower():
            player_id = player['id']
            player_info_req = requests.get(f'https://www.balldontlie.io/api/v1/players/{player_id}')
            player_stats_req = requests.get(
                f'https://www.balldontlie.io/api/v1/season_averages?player_ids[]={player_id}')
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
            ppg = stat_source['pts']
            rebounds = stat_source['reb']
            assists = stat_source['ast']
            steals = stat_source['stl']
            blocks = stat_source['blk']
            turnovers = stat_source['turnover']
            fga = stat_source['fga']
            fta = stat_source['fta']
            # Calculate true shooting percentage
            fg_pct = round(stat_source['fg_pct']*100, 2)
            fg3_pct = round(stat_source['fg3_pct']*100, 2)
            ft_pct = round(stat_source['ft_pct']*100, 2)
            ts = round((ppg/(2*(fga+0.44*fta)))*100,2)
            # Get image from basketball reference
            bbref_id = player_name_id[full_name]
            imageurl = 'https://www.basketball-reference.com/req/202105076/images/players/' + bbref_id + ".jpg"
            yt_query = requests.get(f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=20&q={full_name} highlights&type=video&key={yt_api_key}')
            yt_result = yt_query.json()
            if "error" in yt_result:
                yt_vid_id = False
            else:
                yt_vid_id = yt_result['items'][0]['id']['videoId']
            return render_template('index.html', name=full_name, position=position, points=ppg, rebounds=rebounds,
                                   assists=assists, steals = steals, blocks = blocks, turnovers = turnovers,
                                   fg_pct = fg_pct, fg3_pct = fg3_pct, ft_pct = ft_pct, ts = ts,
                                   height_feet = height_feet, height_inches = height_inches,weight = weight, team = team,
                                   show_stats=True, imageurl = imageurl, player_list = player_name_id, yt_vid_id = yt_vid_id)
    else:
        error_message = "Data not found!"
        return render_template('index.html', error_message = error_message, player_list = player_name_id)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
