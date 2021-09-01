#!/bin/bash

# Projects and crops all files in the corrected directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CORRECTED_PATH='/products/corrected'
CORRECTED_REGEX="*.corrected.vrt"
WARPED_PATH='/products/warped'
#SHAPEFILE="${SCRIPT_DIR}/shapefiles/test.shp"
SHAPEFILE="${SCRIPT_DIR}/shapefiles/subset.shp"
RESOLUTION=90
PROJECTION="EPSG:3031"

mkdir -p "${WARPED_PATH}"

# get shapefile bounds

BOUNDS=$(${SCRIPT_DIR}/get_bounds.sh ${SHAPEFILE})

files=$(find "${CORRECTED_PATH}" -name "${CORRECTED_REGEX}" -printf '%p ' | sort -u)
for file in ${files}; do
    filebase="$(basename ${file} | sed 's/.corrected.tif//g')"
    warped_filename="${filebase}.warped.vrt"
    warped_filepath="${WARPED_PATH}/${warped_filename}"
    #convert them to 3031, generate a vrt with alpha layer, and merge all files together
    #gdalwarp -cutline ${SHAPEFILE} -crop_to_cutline -overwrite -of VRT -novshiftgrid -tr ${RESOLUTION} ${RESOLUTION} -t_srs ${PROJECTION} -r near -multi -of GTiff "${file}" "${warped_filepath}"
    gdalwarp -te ${BOUNDS} -overwrite -of VRT -tr ${RESOLUTION} ${RESOLUTION} -t_srs ${PROJECTION} -r near -multi "${file}" "${warped_filepath}"
    #out_filename="${filebase}.
done
