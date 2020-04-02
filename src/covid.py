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
        ['prep_flow_runtime', 'difference', 'location'],
        axis="columns")
results_df = (
    results_df[results_df["table_names"]=="Daily Summary"]
    .drop(["table_names"], axis='columns')
)
results_df['date'] = pd.to_datetime(results_df['date'])







### US STATISTICS (county level)

states_shp = gpd.read_file(ROOT_DIR.joinpath(
    "data/tl_2017_us_states/tl_2017_us_state.shp"))
states_shp = states_shp[["NAME", "geometry"]]

# County-level shapefiles downloaded from 
# (https://catalog.data.gov/dataset/tiger-line-shapefile-2017-nation-u-s-current-county-and-equivalent-national-shapefile)
counties_shp = gpd.read_file(ROOT_DIR.joinpath(
    "data/tl_2017_us_counties/tl_2017_us_county.shp"))

# County population data downloaded from 
# (https://www.census.gov/data/datasets/time-series/demo/popest/2010s-counties-total.html#par_textimage_70769902)
county_pop = pd.read_csv(ROOT_DIR.joinpath(
    "data/co-est2019-alldata.csv"), usecols=[3, 4, 5, 6, 18])

GEOID = []
for i,row in county_pop.iterrows():
    GEOID.append(
        str(row.STATE).zfill(2) + str(row.COUNTY).zfill(3))
county_pop['GEOID'] = pd.Series(GEOID, dtype=str)
county_pop = county_pop[
    ['GEOID','STNAME','CTYNAME','POPESTIMATE2019']].rename(
        columns={'POPESTIMATE2019': 'Population'})

states_tmp = results_df[
    results_df['country_region']=='US'].drop(
        'country_region', axis='columns')
states_df = (states_tmp.pivot_table(
    values='cases', index=[
        'province_state', 'admin2', 'fips', 
        'lat', 'long', 'date'], columns='case_type')
        .reset_index().rename(
            columns={'Confirmed':'Infected', 'Deaths':'Dead'})
)

states_df['fips'] = [el.zfill(5) for el in states_df.fips.astype(int).astype(str)]
us_cases = states_df[
    ['fips', 'province_state', 'admin2', 'date', 'Infected', 
    'Dead', 'lat', 'long']].rename(columns={'fips': 'GEOID', 
    'province_state': 'State', 'admin2': 'County', 
    'date': 'Date'})

us_cases = us_cases.merge(
    county_pop, how='left', on='GEOID').assign(Infected_1k=
        lambda x: x.Infected / x.Population * 1000)
    
us_cases = us_cases.filter(items=['GEOID', 'State', 'County', 
    'Date', 'Population', 'Infected', 'Infected_1k', 'Dead'])
county_geo = counties_shp[['GEOID', 'geometry']]

us_gdf = gpd.GeoDataFrame(
    us_cases.merge(county_geo, how='left', on='GEOID'), 
    geometry='geometry', crs=county_geo.crs)

us_latest = us_gdf.loc[
    us_gdf['Date']==max(us_gdf['Date'])].drop(['Date'],axis=1)

plt_bnds = gpd.GeoSeries([Polygon(
        zip([-126, -126, -66, -66], [24, 50, 50, 24]))], 
    crs=us_latest.crs)
us_map = us_latest[us_latest.within(plt_bnds.iloc[0])]

fig, ax = plt.subplots(1, 1)
us_map.plot(
    column='Infected_1k', ax=ax, legend=True, 
    legend_kwds={'label': f"Infections per 1k people by county (as of {max(us_cases['Date'])})", 
    'orientation': 'horizontal'})

fig, ax = plt.subplots(1, 1)
us_map.plot(
    column='Dead', ax=ax, legend=True, 
    legend_kwds={'label': f"Deaths by county (as of {max(us_cases['Date'])})", 'orientation': 'horizontal'})





# states_subset = [
#     'New York', 'California', 'Washington', 
#     'District of Columbia', 'Utah', 'Texas'
#     ]
# states_ts = states_df.loc[
#     (states_df['Name'].isin(states_subset)) & 
#     (states_df['date'] > "2020-02-21")]


# fig, ax = plt.subplots()

# for name, group in states_ts.groupby('Name'):
#     group.plot(x='date', y='Infected', ax=ax, label=name)
# plt.yscale('log')
# plt.ylabel('Infected individuals')
# plt.xlabel('Date')

# states_group = states_df.groupby('Name')



### WORLD STATISTICS

# world_df = results_df.pivot_table(
#     values='cases', index=[
#         'country_region', 'province_state', 'admin2', 
#         'lat', 'long', 'date'], 
#         columns='case_type').reset_index().rename(
#         columns={'Confirmed': 'Infected', 'Deaths': 'Dead'})


# countries = gpd.read_file(
#     gpd.datasets.get_path('naturalearth_lowres')).drop(
#         ['continent', 'iso_a3'], axis='columns')

# world_gdf = gpd.GeoDataFrame(
#     world_df.drop(['lat', 'long'], axis='columns'), 
#     geometry=gpd.points_from_xy(world_df.long, world_df.lat), 
#     crs=countries.crs)
# world_gdf = world_gdf.loc[
#     world_gdf['date']==max(world_gdf.date)].drop('date', axis=1)
# world_gdf = world_gdf.dissolve(
#     by='country_region', aggfunc='sum')


# world_map = gpd.sjoin(
#     countries, world_gdf, how='inner', op='contains')
# world_map = world_map[
#     ['index_right', 'pop_est', 'gdp_md_est', 
#     'Infected', 'Dead', 'geometry']].rename(
#         {'index_right': 'Country', 'gdp_md_est': 'GDP'})


# fig, ax = plt.subplots(1, 1)
# world_map.plot(
#     column='Infected', ax=ax, legend=True, 
#     legend_kwds={'label': f"Infections by state (as of {max(world_df['date'])})", 
#     'orientation': 'horizontal'}
# )

# fig, ax = plt.subplots(1, 1)
# world_map.plot(
#     column='Dead', ax=ax, legend=True, 
#     legend_kwds={'label': f"Deaths by state (as of {max(world_df['date'])})", 
#     'orientation': 'horizontal'}
# )

