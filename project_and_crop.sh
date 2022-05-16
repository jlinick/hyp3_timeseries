#!/bin/bash

set -x
set -e
# Projects and crops all files in the corrected directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source ${SCRIPT_DIR}/configs
SHAPEFILE=$(basename ${SHAPEFILE_PATH})
SHAPEFILE_PATH=/data/${SHAPEFILE}

CORRECTED_PATH='/products/corrected'
CORRECTED_REGEX="*.corrected.vrt"
WARPED_PATH='/products/warped'
PROJECTION=$(${SCRIPT_DIR}/get_crs.py --shapefile ${SHAPEFILE_PATH})

mkdir -p "${WARPED_PATH}"

# get shapefile bounds
BOUNDS=$(${SCRIPT_DIR}/get_bounds.sh ${SHAPEFILE_PATH})

files=$(find "${CORRECTED_PATH}" -name "${CORRECTED_REGEX}" -printf '%p ' | sort -u)
echo "generating projected and cropped virtual files..."
for file in ${files}; do
    filebase="$(basename ${file} | sed 's/.corrected.tif//g')"
    warped_filename="${filebase}.warped.vrt"
    warped_filepath="${WARPED_PATH}/${warped_filename}"
    #convert them to same projection, generate a vrt with alpha layer, and merge all files together
    gdalwarp -te ${BOUNDS} -overwrite -of VRT -tr ${RESOLUTION} ${RESOLUTION} -t_srs "${PROJECTION}" -r near -multi "${file}" "${warped_filepath}" > /dev/null
done
