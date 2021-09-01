
## Generating Sentinel-1 HyP3 Timeseries

This package is a Sentinel-1 data retrieval and timeseries generation using the ASF HyP3 layer. While it is currently custom for my work, it can easily be modified to generate timeseries over any region.

### Running

Once everything is set up, all you should need to do is run `./start_container.sh` (which will build the dockerfile if needed and jump you into it) and then the command `run`

This will generate several folders:
* RTC: holds the raw, radiometrically & terrain corrected SLC products
* corrected: holds virtual files from the RTC directory
* warped: holds virtual files that have been cropped and warped to the region of interest
* matched: holds pngs that have been stacked, scaled, & overlayed to generate the timeseries
* timeseries: holds pngs that have been renamed and the animation generated from these

The timeseries animation will be in the timeseries folder.

## Installation/Setup

Here's what needs to be changed to run over something else:
 1.  the `track.py` file contains an ASF query string that should be modified with your area and/or parameters. The ASF API is here: [https://docs.asf.alaska.edu/api/keywords/](https://docs.asf.alaska.edu/api/keywords/)
 2. You need to update your netrc with Earthdata credentials. You can do this by editing ~/.netrc to include: 
```
machine urs.earthdata.nasa.gov login yourusernamehere password yourpasswordhere
machine hyp3-api.asf.alaska.edu login yourusernamehere password yourpasswordhere
```
 3.  You need to generate a shapefile to set the bounds of the timeseries. I suggest you place that in `hyp3_timeseries/shapefiles/subset.shp`. If you name it something else, adjust the SHAPEFILE variable in `project_and_crop.sh` to point to the new file.
 4.  The `start_container.sh` contains references to a local directory on your computer where the output products are placed. This is mounted as /products inside the Docker container. You should change that variable, `LOCAL_PRODUCT_DIR` to point to that path. You should also change `LOCAL_DATA_DIR` to point to the same path.

### Other Notes

All `run.sh` does is call:
`retrieve_data.py`
`move.py`
`project_and_crop.py`
`mean_and_match.py`
`generate_timelapse.py`

In that order.

The `retrieve_data.py` step will submit N jobs to ASF to generate RTC SLC products. It may take them some time to generate the total number of files. Currently, ASF has a limit of 1000 granules/month, so be aware. Also, in the `retrieve_data.py` step a file called `asf-results.json` is placed in the RTC directory. If you want to rerun the retrieval with different query parameters, remove the `asf-results.json` file.

Mostly the other steps are moving around small/virtual files, with the exception of `mean_and_match.py` which attempts to find a mean stack & generate each frame of the timeseries. This may take some time.

You can always restart the process, or run incrementally, by running each file individually.

## Contact

For any questions, please contact:
jlinick@mit.edu
