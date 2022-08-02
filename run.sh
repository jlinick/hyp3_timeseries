#!/bin/bash

set -e
set -x

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source ${SCRIPT_DIR}/configs
SHAPEFILE="$(basename $SHAPEFILE_PATH)"
SHAPEFILE_PATH="/data/${SHAPEFILE}"

if [ ! -f "${SHAPEFILE_PATH}" ]; then
    SHAPEFILE_PATH="${SCRIPT_DIR}/shapefiles/test.shp"
fi



#${SCRIPT_DIR}/retrieve_data.py
#${SCRIPT_DIR}/process_autorift_files.py # converts the nc files to geotiff
#${SCRIPT_DIR}/project_autorift.py # projects all the autorift products as vrts onto the same grid, placing them in the AUTORIFT_PROJECTED folder
${SCRIPT_DIR}/build_autorift_h5.py # builds h5 products for vx, vy, and vm


#${SCRIPT_DIR}/retrieve_data.py --shapefile ${SHAPEFILE_PATH} --start ${START_DATE} --end ${END_DATE} --relativeorbit ${RELATIVE_ORBIT}
#${SCRIPT_DIR}/move.py
#${SCRIPT_DIR}/project_and_crop.sh
#${SCRIPT_DIR}/mean_and_match.py
#${SCRIPT_DIR}/generate_timelapse.py

#rm -rf /products/matched
#rm -rf /products/timelapse
#rm -rf /products/corrected
#rm -rf /products/warped

echo "finished!"
