# This is a script to investigate and plot the progress of 
# COVID-19


# Import required packages
from pathlib import Path
import datadotworld as dw
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon

# Define project root directory
ROOT_DIR = Path(__file__).parent.parent

# Get latest covid data
results = dw.query(
	'covid-19-data-resource-hub/covid-19-case-counts', 
    'SELECT * FROM covid_19_cases')
results_df = results.dataframe.drop(
        ['prep_flow_runtime', 'latest_date', 'difference', 'location'], axis="columns")
results_df = (
    results_df[results_df["table_names"]=="Time Series"]
    .drop(["table_names"], axis='columns')
)
results_df['date'] = pd.to_datetime(results_df['date'])



world_df = results_df.pivot_table(
    values='cases', index=
    ['country_region', 'province_state','lat', 'long', 'date'], columns='case_type').reset_index().rename(
        columns={'Confirmed': 'Infected', 'Deaths': 'Dead'})


countries = gpd.read_file(
    gpd.datasets.get_path('naturalearth_lowres')).drop(
        ['continent', 'iso_a3'], axis='columns')

world_gdf = gpd.GeoDataFrame(
    world_df.drop(['lat', 'long'], axis='columns'), 
    geometry=gpd.points_from_xy(world_df.long, world_df.lat), 
    crs=countries.crs)
world_gdf = world_gdf.loc[
    world_gdf['date']==max(world_gdf.date)].drop('date', axis=1)
world_gdf = world_gdf.dissolve(
    by='country_region', aggfunc='sum')


world_map = gpd.sjoin(
    countries, world_gdf, how='inner', op='contains')
world_map = world_map[
    ['index_right', 'pop_est', 'gdp_md_est', 
    'Infected', 'Dead', 'geometry']].rename(
        {'index_right': 'Country', 'gdp_md_est': 'GDP'})


fig, ax = plt.subplots(1, 1)
world_map.plot(
    column='Infected', ax=ax, legend=True, 
    legend_kwds={'label': f"Infections by state (as of {max(world_df['date'])})", 
    'orientation': 'horizontal'}
)

fig, ax = plt.subplots(1, 1)
world_map.plot(
    column='Dead', ax=ax, legend=True, 
    legend_kwds={'label': f"Deaths by state (as of {max(world_df['date'])})", 
    'orientation': 'horizontal'}
)







states_shp = gpd.read_file(ROOT_DIR.joinpath(
    "data/tl_2017_us_states/tl_2017_us_state.shp"))
states_shp = states_shp[["NAME", "geometry"]]

states_df = (
    world_df[world_df["country_region"] == "US"].drop(
        ["country_region"], axis="columns")
)
states_df = states_df.merge(
    states_shp, how='left', 
    left_on='province_state', right_on='NAME').filter(
        items=['NAME', 'date', 'Infected', 'Dead', 
        'geometry']).rename(columns={"NAME": 'Name'})



states_now = gpd.GeoDataFrame(
    states_df.loc[states_df['date'] == max(states_df['date'])]
    .drop(['date', 'geometry'], axis='columns').reset_index()
    .merge(states_shp, how='left', left_on='Name', 
        right_on='NAME').drop(["NAME", 'index'], 
        axis='columns'), 
    crs=states_shp.crs)


plt_bnds = gpd.GeoSeries([Polygon(
        zip([-126, -126, -66, -66], [24, 50, 50, 24]))], 
    crs=states_shp.crs)
states_map = states_now[states_now.within(plt_bnds.iloc[0])]




fig, ax = plt.subplots(1, 1)
states_map.plot(
    column='Infected', ax=ax, legend=True, 
    legend_kwds={'label': f"Infections by state (as of {max(states_df['date'])})", 
    'orientation': 'horizontal'}
)

fig, ax = plt.subplots(1, 1)
states_map.plot(
    column='Dead', ax=ax, legend=True, 
    legend_kwds={'label': f"Deaths by state (as of {max(states_df['date'])})", 
    'orientation': 'horizontal'}
)


states_subset = [
    'New York', 'California', 'Washington', 
    'District of Columbia', 'Utah', 'Texas'
    ]
states_ts = states_df.loc[
    (states_df['Name'].isin(states_subset)) & 
    (states_df['date'] > "2020-02-21")]


fig, ax = plt.subplots()

for name, group in states_ts.groupby('Name'):
    group.plot(x='date', y='Infected', ax=ax, label=name)
plt.yscale('log')
plt.ylabel('Infected individuals')
plt.xlabel('Date')








