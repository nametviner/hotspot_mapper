import requests
import pandas as pd
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt
import streamlit as st 
from streamlit_folium import folium_static
import h3
import folium
from folium import Map, Marker, GeoJson, Icon
from geojson.feature import *
import json
from PIL import Image as pilim
from folium.plugins import MarkerCluster

nen = '138KfYRtN1iWFwsxht2kTk3oRvTBMawhSChqKxQt87QpJFjf3yD'
time_30_d_ago = (dt.datetime.now() - dt.timedelta(days=30)).isoformat()
headers = {}
city_ids = {'Las Vegas':'bGFzIHZlZ2FzbmV2YWRhdW5pdGVkIHN0YXRlcw','Denver':'ZGVudmVyY29sb3JhZG91bml0ZWQgc3RhdGVz', 'Missoula':'bWlzc291bGFtb250YW5hdW5pdGVkIHN0YXRlcw','Wichita':'d2ljaGl0YWthbnNhc3VuaXRlZCBzdGF0ZXM','Winchester':'d2luY2hlc3Rlcm5ldmFkYXVuaXRlZCBzdGF0ZXM','Phoenix':'cGhvZW5peGFyaXpvbmF1bml0ZWQgc3RhdGVz','Seattle':'c2VhdHRsZXdhc2hpbmd0b251bml0ZWQgc3RhdGVz','Broomfield':'YnJvb21maWVsZGNvbG9yYWRvdW5pdGVkIHN0YXRlcw'}

def get_h3(lat, lng, res):
    h = h3.geo_to_h3(lat = lat,
                 lng = lng,
                 resolution = res)
    return h

def get_mined(address, time = '2021-06-01T00:00:00'):
    if time != '2021-06-01T00:00:00':  
        t = repr(time).replace('\'','')
    else:
        t = time
    url = 'https://api.helium.io/v1/hotspots/' + address + '/rewards/sum' + '?min_time=' + t
    r = requests.get(url=url, headers=headers)
    data = r.json()
    total_mined = data['data']['total']
    return total_mined
def get_info_for_hotspot(hotspot):
    d = {}
    if 'lat' in hotspot.keys():
        d['lat'] = hotspot['lat']
        d['lng'] = hotspot['lng']
        d['city'] = hotspot['geocode']['long_city']
        d['reward scale'] = hotspot['reward_scale']
        d['status'] = hotspot['status']['online']
        d['name'] = hotspot['name']
        d['owner'] = hotspot['owner']
        d['month earnings'] = get_mined(hotspot['address'], time_30_d_ago)
    return d
def get_list_for_city(city):
    list_of_hotspots = []
    respo = city_ids[city]
    url = 'https://api.helium.io/v1/cities/' + respo + '/hotspots'
    r = requests.get(url=url, headers=headers)
    data = r.json()
    if 'cursor' not in data.keys():
        for hotspot in data['data']:
            d = get_info_for_hotspot(hotspot)
            list_of_hotspots.append(d)
        return list_of_hotspots
    while 'cursor' in data.keys():
        r = requests.get(url=url + '?cursor='+ data['cursor'], headers=headers)
        data = r.json()
        for hotspot in data['data']:
            d = get_info_for_hotspot(hotspot)
            list_of_hotspots.append(d)
    return list_of_hotspots
def mapper(city, center_hotspot):
    max_res = 8

    lat_centr_point = [d['lat'] for d in list_of_hotspots if d['name'] == center_hotspot.replace(' ', '-')][0]
    lon_centr_point = [d['lng'] for d in list_of_hotspots if d['name'] == center_hotspot.replace(' ', '-')][0]

    list_hex_res = []
    list_hex_res_geom = []
    list_res = range(4, max_res + 1)
    for resolution in range(4, max_res + 1):
        # index the point in the H3 hexagon of given index resolution
        h = h3.geo_to_h3(lat = lat_centr_point,
                         lng = lon_centr_point,
                         resolution = resolution
                         )

        list_hex_res.append(h)
        # get the geometry of the hexagon and convert to geojson
        h_geom = {"type": "Polygon",
                  "coordinates": [h3.h3_to_geo_boundary(h = h, geo_json = True)]
                  }
        list_hex_res_geom.append(h_geom)


    df_res_point = pd.DataFrame({"res": list_res,
                                 "hex_id": list_hex_res,
                                 "geometry": list_hex_res_geom
                                 })
    df_res_point["hex_id_binary"] = df_res_point["hex_id"].apply(
                                                    lambda x: bin(int(x, 16))[2:])

    pd.set_option('display.max_colwidth', 63)
    
    map_example = Map(location = [lat_centr_point, lon_centr_point],
                  zoom_start = 10,
                  tiles = "cartodbpositron",
                  attr = '''© <a href="http://www.openstreetmap.org/copyright">
                          OpenStreetMap</a>contributors ©
                          <a href="http://cartodb.com/attributions#basemaps">
                          CartoDB</a>'''
                  )

    list_features = []
    for i, row in df_res_point.iterrows():
        feature = Feature(geometry = row["geometry"],
                          id = row["hex_id"],
                          properties = {"resolution": int(row["res"])})
        list_features.append(feature)

    feat_collection = FeatureCollection(list_features)
    geojson_result = json.dumps(feat_collection)


    GeoJson(
            geojson_result,
            style_function = lambda feature: {
                'fillColor': None,
                'color': ("green"
                          if feature['properties']['resolution'] % 2 == 0
                          else "red"),
                'weight': 2,
                'fillOpacity': 0.05
            },
            name = "Example"
        ).add_to(map_example)
    
    mc = MarkerCluster()
    
    for i, row in df.iterrows():
        if row['owner'] == nen:
            mk = Marker(location=[row['lat'], row['lng']], icon=Icon(color='black'), popup= row['name'].replace('-',' ')+' '+ str(row['month earnings']))
        else:
            mk = Marker(location=[row["lat"], row["lng"]], icon=Icon(color='lightgray'), popup= row['name'].replace('-',' ')+' '+ str(row['month earnings']))
        mk.add_to(mc)

    mc.add_to(map_example)
    return map_example

# sidebar 
st.set_page_config(layout = 'wide')

st.sidebar.write("## Helium Mapper")
city_name = st.sidebar.selectbox('Choose a city' ,['Las Vegas', 'Winchester','Wichita','Seattle','Missoula', 'Broomfield','Phoenix','Denver','Ontario'])

list_of_hotspots = get_list_for_city(city_name)
nen_hotspots = list(filter(lambda d: d['owner'] == nen, list_of_hotspots))
df= pd.DataFrame(list_of_hotspots)

if city_name:
    hotspot_centers = ['HOTSPOT CENTER']+[d['name'].replace('-',' ') for d in nen_hotspots]
    locs = st.sidebar.selectbox('Choose a NEN center', hotspot_centers)
    input_center = st.sidebar.text_input('Type a non-NEN center')
    
    if locs != 'HOTSPOT CENTER':
        folium_static(mapper(city_name, locs))
    if input_center:
        folium_static(mapper(city_name, input_center))
