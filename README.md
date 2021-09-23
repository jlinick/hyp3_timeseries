
## Generating Sentinel-1 HyP3 Timeseries

This package is a Sentinel-1 data retrieval and timeseries generation using the ASF HyP3 layer. While it is currently custom for my work, it can be modified to generate timeseries over any region.

### Running

 1. Install docker on your machine. Docker handles setting up the environment so everything can run properly.
 2. Create and/or update your netrc with Earthdata credentials (which can be created [here](https://urs.earthdata.nasa.gov)). Do this by editing ~/.netrc to include: 
```
machine urs.earthdata.nasa.gov login yourusernamehere password yourpasswordhere
machine hyp3-api.asf.alaska.edu login yourusernamehere password yourpasswordhere
```
 3. Create a shapefile that contains a polygon which covers the region you are interested in.
 4. Update the config file with the path to the shapefile on your computer, and the path where you want to save your output products. These are LOCAL_PRODUCT_DIR and SHAPEFILE_PATH respectively. You should also pick a RELATIVE_ORBIT that matches your region, and a START_DATE and END_DATE for the time period you want to generate a timeseries over. 
 5.  Run `start_container.sh`

This will build a docker image, jump into the container, and run a script that should result in a s1-backscatter_timeseries.mp4 file in your output directory.


## Notes

The way this script works is it builds a hyp3_timeseries:latest docker image, and then jumps into that image. It then runs the `run.sh` script.

The run.sh script is simply a wrapper for the following:
`retrieve_data.py`
`move.py`
`project_and_crop.py`
`mean_and_match.py`
`generate_timelapse.py`

This submits a query to ASF to generate products that match your input configs. The script then waits for the products to be generated, downloads those products, projects and crops those products onto the same EPSG, and generates a series of pngs for the timeseries.


### Other Notes

If you add an overview.png image in the shapefiles directory, it will overlay the image on the output products.

The `retrieve_data.py` step will submit N jobs (maximum of 40 at a time) to ASF to generate RTC SLC products. Currently, ASF has a limit of 1000 granules/month, so be aware of this when submitting large orders.

You can always restart the process, or run incrementally, by running each file individually. If you want to jump into the docker image, edit the last line of start_container.sh and remove "/hyp3_timeseries/run.sh". This will jump you into the container with the bash prompt.

One way (there are many) to determine which relative orbit you want to use is to use the UNAVCO SSARA: [https://web-services.unavco.org/brokered/ssara/gui](https://web-services.unavco.org/brokered/ssara/gui) Alternatively, you can remove the --relativeorbit parameter from run.sh, and it will not use orbits.

This tool uses the ASF HyP3 SDK: [ASF HyP3 Documentation](https://hyp3-docs.asf.alaska.edu/using/sdk/) [GitHub SDK](https://github.com/ASFHyP3/hyp3-sdk/tree/main)

## Contact

For any questions, please contact:
jlinick@mit.edu
