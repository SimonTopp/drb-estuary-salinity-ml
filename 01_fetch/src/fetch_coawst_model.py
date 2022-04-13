import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import dask.array as da
import os
from dask.distributed import Client
client = Client()
client

def load_COAWST_model_run(url):
    ds = xr.open_dataset(url, chunks={'ocean_time':720})
    ds = xr.Dataset(ds, coords={'lon': (['eta_rho', 'xi_rho'], nc['lon_rho']),
                          'lat': (['eta_rho', 'xi_rho'], nc['lat_rho']),
                          's': nc['s_rho'])
    print(f'Size: {ds.nbytes / (-10**9)} GB')
    print(run_number)
    return ds
                                
def salt_front_timeseries(write_location, s3_client, s3_bucket, run_number):
    # read river mile coordinates csv
    river_mile_coords = pd.read_csv(river_mile_coords_filepath, index_col=0)
    
    # create array of river miles as points
    target_x = np.array(river_mile_coords.iloc[:,[1]].values).squeeze()
    target_x = xr.DataArray(target_x,dims=["points"]) 
    target_y = np.array(river_mile_coords.iloc[:,[2]].values).squeeze()
    target_y = xr.DataArray(target_y,dims=["points"]) 
    dist_mile = np.array(river_mile_coords.iloc[:,[0]].values).squeeze()
    dist_mile = xr.DataArray(dist_mile,dims=["points"]) 
    
    # select variable for timeseries along shore
    ds = ds.isel(xi_rho=target_x,eta_rho=target_y) 
    
    # assign river mile distance as a new coordinate in dataset
    ds = ds.assign_coords({'dist_mile': dist_mile})
    
    # sort by river mile, subset values from 1st river mile
    salt = ds.isel(s_rho=0).sortby(ds.dist_mile)
    
    #locate saltfront
    saltfront = salt.where(salt < 0.52).where(salt > 0.5)
    saltfront_location = saltfront.where(saltfront.max('ocean_time'))
    
    # convert Datarray to dataframe
    saltfront_location= saltfront_location.to_dataframe()
    
    # tidy dataframe
    df = saltfront_location[saltfront_location['salt'].notna()]
    df = df.droplevel(level=1)
    
    # take daily average
    df = df.resample('1D').mean()
    
    saltfront_data = os.path.join('.', '01_fetch', 'out', f'salt_front_location_from_COAWST_run_{run_number}.csv')
    df.to_csv(saltfront_data, index=False)
    # upload csv with salt front data to S3
        if write_location == 'S3':
        print('uploading to s3')
        s3_client.upload_file(saltfront_data, s3_bucket, '01_fetch/out/'+os.path.basename(saltfront_data))
                                
def main():
    # import config
    with open("01_fetch/fetch_config.yaml", 'r') as stream:
        config = yaml.safe_load(stream)['fetch_COAWST_model_run.py']
        
    # set up write location data outputs
    write_location = config['write_location']
    s3_client = utils.prep_write_location(write_location, config['aws_profile'])
    s3_bucket = config['s3_bucket']
    
    # define model run
    url = config['url']
    u = url.split('/')
    run_number = u[12]
    
    # define csv with river mile coordinates
    river_mile_coords_filepath = config['river_mile_coords_filepath']
if __name__ == '__main__':
    load_COAWST_model_run()
    salt_front_timeseries()
    