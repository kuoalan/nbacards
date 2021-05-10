import os
import requests
from flask import Flask, render_template, json, request, redirect, url_for



app = Flask(__name__)

data_file = os.path.join(app.static_folder, 'data.json')
name_id_file = os.path.join(app.static_folder, 'player_dict.json')

yt_api_key = 'AIzaSyDq5-cCacJJohEAKg6BKy9H7kUR8YqldD0'

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
            position = player_info['position']
            height_feet = player_info['height_feet']
            height_inches = player_info['height_inches']
            weight = player_info['weight_pounds']
            team = player_info['team']['full_name']
            ppg = player_stats['data'][0]['pts']
            rebounds = player_stats['data'][0]['reb']
            assists = player_stats['data'][0]['ast']
            fga = player_stats['data'][0]['fga']
            fta = player_stats['data'][0]['fta']
            fg_pct = round(player_stats['data'][0]['fg_pct']*100, 2)
            fg3_pct = round(player_stats['data'][0]['fg3_pct']*100, 2)
            ft_pct = round(player_stats['data'][0]['ft_pct']*100, 2)
            ts = round((ppg/(2*(fga+0.44*fta)))*100,2)
            print(ts)

            bbref_id = player_name_id[full_name]
            imageurl = 'https://www.basketball-reference.com/req/202105076/images/players/' + bbref_id + ".jpg"
            yt_query = requests.get(f'https://www.googleapis.com/youtube/v3/search?part=snippet&maxResults=20&q={full_name} highlights&type=video&key={yt_api_key}')
            yt_result = yt_query.json()
            if "error" in yt_result:
                yt_vid_id = False
            else:
                yt_vid_id = yt_result['items'][0]['id']['videoId']
            return render_template('index.html', name=full_name, position=position, points=ppg, rebounds=rebounds,
                                   assists=assists, fg_pct = fg_pct, fg3_pct = fg3_pct, ft_pct = ft_pct, ts = ts,
                                   height_feet = height_feet, height_inches = height_inches,weight = weight, team = team,
                                   show_stats=True, imageurl = imageurl, player_list = player_name_id, yt_vid_id = yt_vid_id)
    else:
        error_message = "Data not found!"
        return render_template('index.html', error_message = error_message, player_list = player_name_id)

    # return redirect(url_for('/', name = full_name, position = position, points = ppg, rebounds = rebounds, assists = assists, show_stats = True, **request.args))

if __name__ == '__main__':
    app.run()
