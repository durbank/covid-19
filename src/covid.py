# %% [markdown]
# # PROGRESS OF COVID-19 IN US AND WORLD
# 
# This is a notebook to plot the progress of COVID-19 over time within the USA at the county level.
# It also includes data to investigate the infection spread by country globally.

# %% [markdown]
# We first import all of the necessary packages and extensions.
# %%
# Import required packages
from pathlib import Path
import datadotworld as dw
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import os
import geoviews as gv
from cartopy import crs as ccrs
gv.extension('bokeh', 'matplotlib')

# Define project root directory
# ROOT_DIR = Path(__file__).parent.parent
ROOT_DIR = Path(os.getcwd()).parent


# %% [markdown]
# We next query and download the latest covid data from data.world servers.

# %%
# Get latest covid data
results = dw.query(
	'covid-19-data-resource-hub/covid-19-case-counts', 
    'SELECT * FROM covid_19_cases')
results_df = results.dataframe.drop(
        ['prep_flow_runtime', 'difference'], axis="columns")
results_df = (
    results_df[results_df["table_names"]=="Time Series"]
    .drop(["table_names"], axis='columns')
)
results_df['date'] = pd.to_datetime(results_df['date'])


# %%

### US STATISTICS (county level)

# Import shapefile of US states and 
states_shp = gpd.read_file(ROOT_DIR.joinpath(
    "data/tl_2017_us_states/tl_2017_us_state.shp"))
states_shp = states_shp[["NAME", "geometry"]].rename(
    columns={'NAME': 'State'})

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
    county_pop, how='left', on='GEOID').assign(
        Infected_100k=lambda x: x.Infected / x.Population * 100000)
    
us_cases = us_cases.filter(items=[
    'GEOID', 'State', 'County', 'Date', 'Population', 
    'Infected', 'Infected_100k', 'Dead'])

county_geo = counties_shp[['GEOID', 'geometry']]

us_gdf = gpd.GeoDataFrame(
    us_cases.merge(county_geo, how='left', on='GEOID'), 
    geometry='geometry', crs=county_geo.crs)
us_gdf = us_gdf.dropna().sort_values(['GEOID', 'Date'])


latest_idx = us_gdf.groupby(['GEOID'])['Date'].idxmax()
us_latest = us_gdf.loc[latest_idx].drop(
    'Date', axis=1)
us_latest = us_latest[us_latest['Infected'] > 0]


# ### US Statistics (state level)

states_vals = us_latest.groupby('State').sum()
states_vals['Infected_100k'] = (100000 * 
states_vals.Infected / states_vals.Population)
us_states = states_shp.merge(states_vals, on='State')


# %%

gv.Polygons(
    us_states, vdims=[
        ('Infected','Total Infected'), 
        'State']).options(
        tools=['hover'], width=800, height=500, logz=True,
        projection=ccrs.AlbersEqualArea(-95, 40), 
        colorbar=True, cmap='inferno'
)

# %%

clipping = {'min': 'white', 'max': 'red', 'NaN': 'gray'}
county_map = gv.Polygons(
    us_latest, vdims=[
        ('Infected_100k','Infections per 100k'), 
        ('County', 'County'), ('State', 'State'), 
        ('Population', 'Population')]).options(
        tools=['hover'], logz=True, width=800, height=500, 
        projection=ccrs.AlbersEqualArea(-95, 40), 
        color_index='Infected_100k', colorbar=True, 
        cmap='inferno')
county_map#.redim.range(z=(0,100))



# %%

# Need better implementation of large number of polygons 
# while plotting. The following websites have ideas on how 
# to address this
# https://www.data-dive.com/cologne-bike-rentals-interactive-map-bokeh
# https://www.data-dive.com/interactive-maps-made-easy-geoviews
# https://data-dive.com/interactive-large-data-plots-datashader



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



# %%

### WORLD STATISTICS

countries_shp = gpd.read_file(
    gpd.datasets.get_path('naturalearth_lowres')).drop(
        ['continent', 'iso_a3'], axis='columns')


world_tmp = results_df.drop(
    ['province_state', 'admin2', 'combined_key', 'fips'],
    axis='columns')
country_tmp = world_tmp[
    ['country_region', 'lat', 'long']].groupby(
        'country_region').mean()
country_loc = gpd.GeoDataFrame(country_tmp.index, 
    geometry = gpd.points_from_xy(
        country_tmp.long, country_tmp.lat), 
    crs='EPSG:4326').rename(
        columns={'country_region': 'Country'})
world_date = world_tmp.drop(
    ['lat', 'long'], axis=1).pivot_table(
        values='cases', index=['country_region', 'date'], 
        columns='case_type').reset_index().rename(
            columns={'country_region': 'Country', 
            'date': 'Date', 'Confirmed': 'Infected', 
            'Deaths': 'Dead'})

world_cases_pts = country_loc.merge(
    world_date.groupby('Country').sum().reset_index(), 
    how='left', on='Country')

world_cases = gpd.sjoin(countries_shp, world_cases_pts, 
    how='inner', op='contains')[
        ['Country', 'geometry', 'pop_est', 
        'gdp_md_est', 'Infected', 'Dead']].rename(
            columns={'pop_est': 'Population', 
            'gdp_md_est': 'GDP'})
world_cases = world_cases.assign(
    Infected_100k=lambda x: x.Infected / x.Population 
    * 100000)


# %%

gv.Polygons(
    world_cases, vdims=[
        ('Infected','Total Infections'), 
        'Country']).options(
        tools=['hover'], width=800, height=500, logz=True,
        projection=ccrs.Robinson(), cmap='inferno',
        colorbar=True
)

# %%

gv.Polygons(
    world_cases, vdims=[
        ('Infected_100k','Infected per 100k'), 
        'Country']).options(
        tools=['hover'], width=800, height=500, logz=True,
        projection=ccrs.Robinson(), cmap='inferno', 
        colorbar=True
)




# %% 

# os.system('jupyter nbconvert --to html yourNotebook.ipynb')