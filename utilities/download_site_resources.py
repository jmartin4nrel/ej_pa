import os
import time
import numpy as np
from mpi4py import MPI

from hopp.simulation.technologies.resource import (
    SolarResource,
    WindResource,
)
from hopp.utilities.keys import set_nrel_key_dot_env

rank = MPI.COMM_WORLD.Get_rank()
set_nrel_key_dot_env() 

def download_site_resources(config,fp):

    lat = config.hopp_config["site"]["data"]["lat"]
    lon = config.hopp_config["site"]["data"]["lon"]
    year = config.hopp_config['site']['data']['year']
    
    solar_fp = fp+'solar/{:.3f}_{:.3f}_{:d}.csv'.format(lat,lon,year)
    wind_fp = fp+'wind/{:.3f}_{:.3f}_{:d}.csv'.format(lat,lon,year)
    
    # Only download the file if it does not already exist
    # Sleep <rank> seconds to avoid API timeouts when multiprocessing
    if not os.path.exists(solar_fp):
        time.sleep(rank*4)
        SolarResource(lat, lon, year, filepath=solar_fp)
    if not os.path.exists(wind_fp):
        time.sleep(rank*4+2)
        WindResource(lat, lon, year, filepath=wind_fp,
                wind_turbine_hub_ht=config.turbine_config['hub_height'])