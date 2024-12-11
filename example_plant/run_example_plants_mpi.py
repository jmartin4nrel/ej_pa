'''
Sweeps through example_plants with modified ores and technologies (hopefully also locations)
Based off of NED-toolbox/toolbox/simulation/run_offshore_onshore_baseline_mpi.py
'''

# All imports copied from NED-toolbox/toolbox/simulation/run_offshore_onshore_baseline_mpi.py
import pandas as pd
import yaml
import os
import time
import logging
from pathlib import Path
from hopp.utilities import load_yaml
import copy
import sys
from mpi4py import MPI
from datetime import datetime

# This is a new import not in HOPP/GreenHEART reqs
# from yamlinclude import YamlIncludeConstructor

# Changed the imported function for multiprocessing from run_offgrid_onshore to run_example_plant
from run_example_plant import run_example_plant

# Made my own logger from NED-toolbox logger
from utilities.logger import mpi_logger as mpi_log
from utilities.logger import main_logger as main_log

ROOT_DIR = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT_DIR/"example_plant/input"

sitelist_all = INPUT_DIR/'multiprocess/sitelist.csv'

sitelist_locs = INPUT_DIR/'multiprocess/sitelist_just_loc.csv'

# Set to False to use to old, previously-calculated location data
rerun_locs = True

# Parallel job is "do_something" - run_example_plant replaces run_baseline_site
def do_something(inputs,site_id):
    mpi_log.info("Site {}: starting".format(site_id))
    run_pre_iron, ore, tech, location = inputs
    run_example_plant(run_pre_iron, ore, tech, location)
    mpi_log.info("Site {}: complete".format(site_id))

start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()

# Mostly the same
def main(sitelist,inputs,verbose = True):
    """Main function
    Basic MPI job for embarrassingly paraller job:
    read data for multiple sites(gids) from one WTK .h5 file
    compute somthing (windspeed min, max, mean) for each site(gid)
    write results to .csv file for each site(gid)
    each rank will get about equal number of sites(gids) to process
    """

    ### input
    main_log.info(f"START TIME: {start_time}")
    main_log.info("number of ranks: {}".format(size))
    main_log.info("number of sites: {}".format(len(sitelist)))
    site_idxs = sitelist.index
    if rank == 0:
        print(" i'm rank {}:".format(rank))
        ################################ split site_idx's
        s_list = site_idxs.tolist()
        # check if number of ranks <= number of tasks
        if size > len(s_list):
            print(
                "number of scenarios {} < number of ranks {}, abborting...".format(
                    len(s_list), size
                )
            )
            sys.exit()

        # split them into chunks (number of chunks = number of ranks)
        chunk_size = len(s_list) // size

        remainder_size = len(s_list) % size

        s_list_chunks = [
            s_list[i : i + chunk_size] for i in range(0, size * chunk_size, chunk_size)
        ]
        # distribute remainder to chunks
        for i in range(-remainder_size, 0):
            s_list_chunks[i].append(s_list[i])
        if verbose:
            print(f"\n s_list_chunks {s_list_chunks}")
        main_log.info(f"s_list_chunks {s_list_chunks}")
    else:
        s_list_chunks = None

    ### scatter
    s_list_chunks = comm.scatter(s_list_chunks, root=0)
    if verbose:
        print(f"\n rank {rank} has sites {s_list_chunks} to process")
    main_log.info(f"rank {rank} has sites {s_list_chunks} to process")

    # ### run sites in serial
    for i, gid in enumerate(s_list_chunks):
        # time.sleep(rank * 5)
        if verbose:
            print(f"rank {rank} now processing its sites in serial: site gid {gid}")
        mpi_log.info(f"rank {rank} now processing its sites in serial: Site {gid}")
        inputs_copied = [copy.deepcopy(inpt) for inpt in inputs[gid]]
        do_something(inputs_copied,gid)
    if verbose:
        print(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")
    mpi_log.info(f"rank {rank}: ellapsed time: {datetime.now() - start_time}")

# This function reads a very basic placeholder sitelist
def setup_sites(sitelist_fp, run_pre_iron=False):

    sites = pd.read_csv(sitelist_fp)
    
    inputs = []
    for i in range(sites.shape[0]):
        site = sites.loc[i]
        inputs.append([run_pre_iron,
                       site.loc['ore'],
                       site.loc['tech'],
                       (site.loc['latitude'],site.loc['longitude'])])

    return sites, inputs


if __name__ == "__main__":
    if len(sys.argv)<3:
        n_sites = 4 
        start_idx = 0
    else:
        n_sites = int(sys.argv[1])
        start_idx = int(sys.argv[2])

    input_filepath = INPUT_DIR/'multiprocess/example.yaml'
    input_config = load_yaml(input_filepath)

    # below is to run on HPC
    # input_config["renewable_resource_origin"] = "HPC" #"API" or "HPC"
    # input_config["hpc_or_local"] = "HPC"
    # input_config["output_dir"] = "/kfs2/projects/hopp/ned-results/v1"

    # below is to run locally
    input_config["renewable_resource_origin"] = "API" #"API" or "HPC"
    input_config["hpc_or_local"] = "local"
    if "env_path" in input_config:
        input_config.pop("env_path")
    input_config.pop("output_dir")
    
    # Pre-populate model with location-specific data - DO run pre-iron steps of GreenHEART
    
    if rerun_locs:

        site_list_locs, inputs = setup_sites(sitelist_locs, True)
        main_log.info("set up runs")
    
        end_idx = start_idx + n_sites
        if end_idx>=len(site_list_locs):
            sitelist_locs = site_list_locs.iloc[start_idx:]
        else:
            sitelist_locs = site_list_locs.iloc[start_idx:start_idx+n_sites]
        
        main(site_list_locs,inputs)

    # Run all technologies across locations - DON'T run pre-iron steps of GreenHEART

    site_list_all, inputs = setup_sites(sitelist_all, False)
    main_log.info("set up runs")
 
    end_idx = start_idx + n_sites
    if end_idx>=len(site_list_all):
        sitelist_all = site_list_all.iloc[start_idx:]
    else:
        sitelist_all = site_list_all.iloc[start_idx:start_idx+n_sites]
    
    main(site_list_all,inputs)