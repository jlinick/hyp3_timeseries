#!/usr/bin/env python3

'''prints a crs to the screen, determined by the centroid latitude of the input shapefile'''

import os
import argparse
import geopandas


def main(shapefile=False):
    if shapefile is False:
        print('ERROR')
    if not os.path.exists(shapefile):
        return
    data = geopandas.read_file(shapefile)
    #data = data.to_crs(epsg=4326)
    centroid = data.exterior.geometry.centroid.to_crs(epsg=4326)
    lat = centroid.y.iloc[0]
    if lat > 70:
        print('EPSG:3995')
    elif lat < -70:
        print('EPSG:3031')
    else:
        print('EPSG:4326')

def parser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Determines the crs to use for the given shapefile")
    parse.add_argument("--shapefile", required=True, help="input shapefile or kml file")
    return parse


if __name__ == '__main__':
    args = parser().parse_args()
    main(shapefile=args.shapefile)
