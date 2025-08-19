# api/views.py

import os
import requests
import pandas as pd
from rest_framework.response import Response
from rest_framework.decorators import api_view
from decouple import config
from datetime import datetime, timezone
from decouple import config

@api_view(['GET'])
def get_arb_results(request):
    API_KEY = config('API_KEY')
    
     
    bookmakers_param = request.query_params.get('flag', None)
    live_param = request.query_params.get('includeLiveEvents', None)
    print(bookmakers_param)
    print (live_param)
    if bookmakers_param == '🇨🇦':
        REGIONS = 'us,uk'
        desired_bookmakers = ['betmgm','betrivers','draftkings','fanduel']
    else:
        desired_bookmakers = None
        REGIONS = "us"
    print(desired_bookmakers)


    
    SPORT = "upcoming"
    
    MARKETS = 'h2h,spreads,totals'
    ODDS_FORMAT = 'decimal'
    DATE_FORMAT = 'iso'

    odds_response = requests.get(
        f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds',
        params={
            'api_key': API_KEY,
            'regions': REGIONS,
            'markets': MARKETS,
            'oddsFormat': ODDS_FORMAT,
            'dateFormat': DATE_FORMAT,
        }
    )

    if odds_response.status_code != 200:
        return Response({'error': 'Failed to fetch odds data'}, status=odds_response.status_code)

    print("Requests remaining:", odds_response.headers.get('x-requests-remaining'))
    print("Requests used:", odds_response.headers.get('x-requests-used'))
    print("Last request cost:", odds_response.headers.get('x-requests-last'))

    odds_json = odds_response.json()

    flattened_data = []

    for game in odds_json:
        for bookmaker in game.get('bookmakers', []):
            if desired_bookmakers and bookmaker.get('key') not in desired_bookmakers:
                continue
            for market in bookmaker.get('markets', []):
                for outcome in market.get('outcomes', []):
                    flattened_data.append({
                        'game_id': game.get('id'),
                        'sport_key': game.get('sport_key'),
                        'sport_title': game.get('sport_title'),
                        'commence_time': game.get('commence_time'),
                        'home_team': game.get('home_team'),
                        'away_team': game.get('away_team'),
                        'bookmaker': bookmaker.get('title'),
                        'market_key': market.get('key'),
                        'outcome_name': outcome.get('name'),
                        'outcome_price': outcome.get('price'),
                        'point': outcome.get('point', None)
                    })
    
    df = pd.DataFrame(flattened_data)
    dfdet = df[df['market_key'].isin(['h2h', 'totals', 'spread'])]



    def arbcheck(x, y):
        return 1 - ((1 / x) + (1 / y))

    grouped = dfdet.groupby('game_id')
    arb_results = []
    current_time = datetime.now(timezone.utc)  

    for game_id, group in grouped:
        for outcome_1 in group.itertuples():
        
            commence_time_1 = datetime.strptime(outcome_1.commence_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        
            if live_param == 'false' and commence_time_1 < current_time:
                continue
        
            for outcome_2 in group.itertuples():
            
                commence_time_2 = datetime.strptime(outcome_2.commence_time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            
            
                if live_param == 'false' and commence_time_2 < current_time:
                    continue
            
                if (
                    outcome_1.outcome_name != outcome_2.outcome_name and
                    outcome_1.market_key == outcome_2.market_key and
                    outcome_1.outcome_name != 'Draw' and
                    outcome_2.outcome_name != 'Draw' and
                    'soccer' not in outcome_1.sport_key and
                    'soccer' not in outcome_2.sport_key
                ):
                    bookmaker_1 = outcome_1.bookmaker
                    bookmaker_2 = outcome_2.bookmaker
                    odd_1 = outcome_1.outcome_price
                    odd_2 = outcome_2.outcome_price

                    arb_result = arbcheck(odd_1, odd_2)

                    if arb_result > -0:
                        arb_results.append({
                            'game_id': game_id,
                            'home_team': outcome_1.home_team,
                            'away_team': outcome_1.away_team,
                            'outcome_name_1': outcome_1.outcome_name,
                            'outcome_name_2': outcome_2.outcome_name,
                            'bookmaker_1': bookmaker_1,
                            'bookmaker_2': bookmaker_2,
                            'odds_1': odd_1,
                            'odds_2': odd_2,
                            'arb_check': arb_result,
                            'market_key': outcome_1.market_key,
                            'sport_title': outcome_1.sport_title
                        })

    if not arb_results:
        return Response({'message': 'No arbitrage opportunities found.'}, status=200)

    arb_df = pd.DataFrame(arb_results)
    arb_df = arb_df.sort_values('arb_check', ascending=False)
    arb_df = arb_df.drop_duplicates(subset=['arb_check'], keep='first')
    df_bottom_5 = arb_df.head(50)

    return Response(df_bottom_5.to_dict(orient='records'))


