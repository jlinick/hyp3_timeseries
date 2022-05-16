#!/usr/bin/env python3

'''Combines the products in the warped directory into an h5 file'''

import os
import re
import fiona
import numpy as np
from osgeo import gdal
from PIL import Image
from tqdm import tqdm
from datetime import datetime as dt
from skimage.measure import block_reduce
import matplotlib.pyplot as plt
from scipy.optimize import minimize

import iceutils as ice

INFOLDER='/products/warped'
OUTFOLDER='/products/'
OUTFILE='sar.h5'
IN_REGEX=r'^S1[AB].*?_([0-9]{8}).*.warped.vrt$' # for dates
BLACKLIST_DATES = ['2016-01-17', '2016-07-30', '2016-10-07', '2016-10-13', '2018-01-03'] # custom list for dates with poor/bad data (will ignore these dates)

def main():
    files = get_matching(INFOLDER)
    if not os.path.exists(OUTFOLDER):
        os.makedirs(OUTFOLDER)
    
    # load overview (map legend, north arrow, shapefiles, etc)
    #overview = None
    #if os.path.exists(OVERVIEW_PATH):
    #    overview = plt.imread(OVERVIEW_PATH)

    #base = np.full_like(load_gdal(files[0]), fill_value=pmin)
    fil_dict = sort_into_dict(files) # file paths with their associated dates
    dates = sorted(fil_dict.keys())

    # init stack
    stack_path = os.path.join(OUTFOLDER, OUTFILE)
    ref_hdr = ice.RasterInfo(files[0])
    tdec = np.array([ice.datestr2tdec(pydtime=date) for date in dates])
    stack = ice.Stack(stack_path, mode='w', init_tdec= tdec, init_rasterinfo=ref_hdr)
    stack.init_default_datasets(weights=True, chunks=None)

    # for each date, combine the observations and save to the stack
    print('saving stack to {}'.format(stack_path))
    for i, date in tqdm(enumerate(dates)):
        if date.strftime('%Y-%m-%d') in BLACKLIST_DATES:
            continue
        fils = fil_dict.get(date)
        arrs = [] 
        # combine arrays for the given date
        for fil in fils:
            arr = load_gdal(fil)
            arrs.append(arr)
        combined = combine(arrs) # the combined array for that date, add it to the Stack
        stack.set_slice(i, combined, 'data')

def combine(arrays):
    '''combine multiple images into a single array (if needed). returns the combined array'''
    stack = np.ma.dstack(arrays)
    # get the mean of the stack
    combined = np.ma.mean(stack, axis=2)
    return combined

def scale(arr, clim):
    '''returns the scaled array from clim (min,max) bounds to 1-255 integer array (since we use 0 as mask)'''
    return ((arr-clim[0])/abs(clim[1]-clim[0])*254 + 1).astype(int)

def save_gdal(arr, filename):
    np.ma.set_fill_value(arr, 0.)
    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(filename, xsize=arr.shape[1], ysize=arr.shape[0], bands=1, eType=gdal.GDT_Float32)
    dst_ds.GetRasterBand(1).WriteArray(arr)
    dst_ds = None # close raster

def load_gdal(filename):
    ds = gdal.Open(filename)
    myarray = np.ma.masked_less_equal(np.ma.array(ds.GetRasterBand(1).ReadAsArray()),0)
    return myarray

def load_binned(filename):
    return block_reduce(load_gdal(filename), block_size=(N,N), func=np.ma.median)

def get_matching(infolder):
    file_list = []
    return sorted([os.path.join(infolder,f) for f in os.listdir(infolder) if re.match(IN_REGEX,f)], key=get_date)

def get_date(path):
    '''parses the datetime from the path name'''
    filename = os.path.basename(path)
    datestr = re.search(IN_REGEX, filename).group(1)
    return dt.strptime(datestr, '%Y%m%d')

def sort_into_dict(fils):
    '''sorts into dict where key is the date'''
    fil_dict = {}
    for fil in fils:
        fil_dict.setdefault(get_date(fil),[]).append(fil)
    return fil_dict

if __name__ == '__main__':
    main()
