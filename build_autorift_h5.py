#!/usr/bin/env python3

'''Combines the autorift products into h5 files'''

import os
import re
import sys
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


resolution = os.getenv('RESOLUTION')
if resolution is None:
    raise Exception("please run 'source configs' to load ENVS")


INFOLDER='/products/AUTORIFT_PROJECTED'
OUTFOLDER='/products/AUTORIFT_H5'
OUTFILE='thwaites.autorift.' + str(resolution) + '.{}.h5'


DATE_REGEX=r'^S1AR_([0-9]{4}-[0-9]{2}-[0-9]{2})-([0-9]{4}-[0-9]{2}-[0-9]{2}).*.vrt$'
VX_IN_REGEX=r'^S1AR_([0-9]{4}-[0-9]{2}-[0-9]{2})-([0-9]{4}-[0-9]{2}-[0-9]{2}).*.vx.vrt$'
VY_IN_REGEX=r'^S1AR_([0-9]{4}-[0-9]{2}-[0-9]{2})-([0-9]{4}-[0-9]{2}-[0-9]{2}).*.vy.vrt$' 
V_IN_REGEX=r'^S1AR_([0-9]{4}-[0-9]{2}-[0-9]{2})-([0-9]{4}-[0-9]{2}-[0-9]{2}).*.v.vrt$' 
V_ERR_IN_REGEX=r'^S1AR_([0-9]{4}-[0-9]{2}-[0-9]{2})-([0-9]{4}-[0-9]{2}-[0-9]{2}).*.v_error.vrt$' 

BLACKLIST_DATES = [] # custom list for dates with poor/bad data (will ignore these dates)


def main(REGEX=V_IN_REGEX, NAME='v'):
    files = get_matching(INFOLDER, REGEX)
    if not os.path.exists(OUTFOLDER):
        os.makedirs(OUTFOLDER)
    
    fil_dict = sort_into_dict(files) # file paths with their associated dates
    dates = sorted(fil_dict.keys())

    # init stack
    stack_path = os.path.join(OUTFOLDER, OUTFILE.format(NAME))
    ref_hdr = ice.RasterInfo(files[0])
    tdec = np.array([ice.datestr2tdec(dateobj=date) for date in dates])
    stack = ice.Stack(stack_path, mode='w', init_tdec= tdec, init_rasterinfo=ref_hdr)
    #stack.init_default_datasets(weights=True, chunks=None)
    shape = (len(dates), ref_hdr.ny, ref_hdr.nx) #t, y, x
    stack.create_dataset('data', shape, dtype='f')
            
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
            arr = np.ma.masked_equal(arr, -32767) # mask out zeros
            count = np.ma.count_masked(arr)
            #print('input array mask count: {}'.format(count))
            arr = arr / 1000. # convert from m/yr to km/yr
            #print('new masked array: {}'.format(type(arr)))
            #print('masked values in array: {}'.format(np.ma.count_masked(arr)))
            arrs.append(arr)
        combined = combine(arrs) # the combined array for that date, add it to the Stack
        #combined = np.nan_to_num(combined, nan=-32767)
        #print('combined array nans: {}'.format(np.count_nonzero(np.isnan(combined))))
        #nancount = np.ma.count_masked(combined)
        #print('combined array mask count: {}'.format(nancount))
        stack.set_slice(i, combined, 'data')

def combine(arrays):
    '''combine multiple images into a single array (if needed). returns the combined array'''
    stack = np.ma.dstack(arrays)
    # get the mean of the stack
    combined = np.nanmean(stack, axis=2)
    return combined

def scale(arr, clim):
    '''returns the scaled array from clim (min,max) bounds to 1-255 integer array (since we use 0 as mask)'''
    return ((arr-clim[0])/abs(clim[1]-clim[0])*254 + 1).astype(int)

def save_gdal(arr, filename):
    np.ma.set_fill_value(arr, 0.)
    driver = gdal.GetDriverByName('GTiff')
    dst_ds = driver.Create(filename, xsize=arr.shape[1], ysize=arr.shape[0], bands=1, eType=gdal.GDT_Float32)
    dst_ds.GetRasterBand(1).SetNoDataValue(0) 
    dst_ds.GetRasterBand(1).WriteArray(arr)
    dst_ds = None # close raster

def load_gdal(filename):
    ds = gdal.Open(filename)
    #myarray = np.ma.masked_less_equal(np.ma.array(ds.GetRasterBand(1).ReadAsArray()),0)
    myarray = ds.GetRasterBand(1).ReadAsArray()
    #print('gdal array type: {}'.format(type(myarray)))
    return myarray

def load_binned(filename):
    return block_reduce(load_gdal(filename), block_size=(N,N), func=np.ma.median)

def get_matching(infolder, REGEX):
    file_list = []
    return sorted([os.path.join(infolder,f) for f in os.listdir(infolder) if re.match(REGEX,f)], key=get_date)

def get_date(path):
    '''parses the datetime from the path name'''
    filename = os.path.basename(path)
    datestr = re.search(DATE_REGEX, filename).group(1)
    return dt.strptime(datestr, '%Y-%m-%d')

def sort_into_dict(fils):
    '''sorts into dict where key is the date'''
    fil_dict = {}
    for fil in fils:
        fil_dict.setdefault(get_date(fil),[]).append(fil)
    return fil_dict

if __name__ == '__main__':
    
    main(REGEX=VX_IN_REGEX, NAME='vx')
    main(REGEX=VY_IN_REGEX, NAME='vy')
    main(REGEX=V_IN_REGEX, NAME='v')
    main(REGEX=V_ERR_IN_REGEX, NAME='v_err')
