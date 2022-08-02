#!/bin/bash

set -x
set -e
# Projects and crops all files in the corrected directory

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
source ${SCRIPT_DIR}/configs
SHAPEFILE=$(basename ${SHAPEFILE_PATH})
#SHAPEFILE_PATH=/data/${SHAPEFILE}
SHAPEFILE_PATH='/data/thwaites_outline.shp'

IN_PATH='/products/AUTORIFT'
IN_REGEX='S1AR_*.tif'
OUT_PATH='/products/AUTORIFT_PROJECTED'
PROJECTION=$(${SCRIPT_DIR}/get_crs.py --shapefile ${SHAPEFILE_PATH})

mkdir -p "${OUT_PATH}"

# get shapefile bounds
BOUNDS=$(${SCRIPT_DIR}/get_bounds.sh ${SHAPEFILE_PATH})

files=$(find "${IN_PATH}" -name "${IN_REGEX}" -printf '%p ' | sort -u)
echo "generating projected and cropped virtual files..."
for file in ${files}; do
    filebase="$(basename ${file} | sed 's/.tif//g')"
    out_filename="${filebase}.${RESOLUTION}.vrt"
    out_filepath="${OUT_PATH}/${out_filename}"
    #convert them to same projection, generate a vrt with alpha layer, and merge all files together
    gdalwarp -te ${BOUNDS} -overwrite -of VRT -tr ${RESOLUTION} ${RESOLUTION} -t_srs "${PROJECTION}" -r average -multi "${file}" "${out_filepath}" > /dev/null
done
