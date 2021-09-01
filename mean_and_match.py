#!/usr/bin/env python3

'''Generates a mean image across the stack, then does a dynamic histogram normalization. Outputs pngs'''

import os
import re
import sys
import subprocess
import fiona
import numpy as np
from osgeo import gdal
from PIL import Image
from datetime import datetime as dt
from skimage.measure import block_reduce
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from skimage.exposure import match_histograms

INFOLDER='/products/warped'
OUTFOLDER='/products/matched'
RANGE=[.5,98] # percentile range to scale output images
#S1_REGEX='S1.*warped.tif'
IN_REGEX=r'^S1[AB].*?_([0-9]{8}).*.warped.vrt$' # for dates
N=2 # how much to bin the images (N,N)
script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
SHAPEFILE=os.path.join(script_dir, 'shapefiles/subset.shp')
WATER_MASK= os.path.join(script_dir, 'shapefiles/Mask_Antarctica_v02.tif')

#OUTPUT_DIR = '/output'
REMOVE='.temp'#'.merged'

def main():
    # get filenames matching regex & determine associated outfile names
    files = get_matching(INFOLDER)
    
    # load the rasters into a 3d numpy array, binning them by NxN (so they fit in memory & are more robust)
    print('loading {} files into stack and generating mean...'.format(len(files)))

    #stack = np.ma.dstack([load_binned(fil) for fil in files]) # use binned if sizes are over RAM/swap
    #stack = np.ma.dstack([load_gdal(fil) for fil in files])
    # get the mean of the stack
    #med = np.ma.mean(stack, axis=2)
    water_mask = get_water_mask(files)
    print('water mask size: {}'.format(water_mask.shape))
    med = efficient_mean(files, water_mask)

    #del stack # clear the binned stack from memory
    pmin, pmax = np.percentile(med, RANGE) # get values of percentiles
    print('min: {}, max: {}'.format(pmin, pmax)) 
    #pmin=0.
    #pmax=0.67
    if not os.path.exists(OUTFOLDER):
        os.makedirs(OUTFOLDER)
    save(med, os.path.join(OUTFOLDER, 'median.png'), (pmin,pmax)) # save the median binned image
    #save_gdal(med, os.path.join(OUTFOLDER, 'median.tif')) # save the median binned image
    
    # load overview (map legend, north arrow, shapefiles, etc)
    overview=None
    overview_path = '/tops/HyP3/shapefiles/overview.png'
    if os.path.exists(overview_path):
        overview = plt.imread(overview_path)

    # apply the histogram normalization to each image
    print('applying corrections and saving files...')
    base = np.full_like(med, fill_value=pmin)
    fil_dict = sort_into_dict(files)
    for date in sorted(fil_dict.keys()):
        fils = fil_dict.get(date)
        base = apply_scaling(fils, med, (pmin,pmax), overview=overview, base=base, date=date)

def get_water_mask(files):
    # get bounds of image
    cmd = ' '.join([os.path.join(script_dir, 'get_bounds.sh'), SHAPEFILE])
    print(cmd)
    bounds = subprocess.check_output(cmd, shell=True).strip().decode('ascii')
    print('image bounds: {}'.format(bounds))
    # crop mask to proper bounds
    output_file = os.path.join(script_dir, 'shapefiles', 'mask.crop.tif') 
    if not os.path.exists(output_file):
        cmd = 'gdalwarp -te {} -of GTiff -t_srs EPSG:3031 -r near -multi {} {}'.format(bounds, WATER_MASK, output_file)
        os.system(cmd)
    print(cmd)
    water_mask = load_gdal(output_file)
    land_only = np.ma.masked_less(water_mask, 255)
    return match_size(land_only.mask, load_gdal(files[0]))

def match_size(arrayA, arrayB):
    '''matches the size of arrayA to arrayB'''
    im = Image.fromarray(arrayA)
    return np.array(im.resize((arrayB.shape[1], arrayB.shape[0]), resample=0))

def apply_scaling(fil_paths, med, minmax, overview=None, base=None, date=None):
    '''apply image scaling and save the file'''
    pmin,pmax = minmax
    arrays = []
    for fil_path in fil_paths: # these are multiple files all on the same date
        arr = load_gdal(fil_path)
        med.mask = arr.mask # ensure the histogram comparisons are over the same data
        #matched = np.ma.array(match_histograms(arr, med)) # THIS DOES DYNAMIC HISTOGRAM MATCHING
        #matched = np.ma.array(linear_correction(arr, med)) # THIS DOES A LINEAR SCALING + OFFSET
        matched = np.ma.array(gamma_correction(arr, med)) # THIS DOES A GAMMA SCALING
        matched.mask = arr.mask # ensure the mask stays the same
        arrays.append(matched)
    # combine the matched arrays
    combined = combine(arrays)

    #np.ma.set_fill_value(matched, 0.) # and ensure the mask is set to zero
    #matched = np.ma.array(match_histograms(arr, med))
    outfile = 'S1-{}.matched.png'.format(date.strftime('%Y%m%d'))
    #outfile = os.path.basename(fil_path).replace('warped.tif', 'matched.png')
    outpath = os.path.join(OUTFOLDER, outfile)
    base = np.ma.array(np.ma.filled(combined, fill_value=base)) # we're going to update the base with the current observation
    save(base, outpath, (pmin,pmax), date=date, overview=overview)
    #med = np.ma.array(np.ma.filled(arr, fill_value=med)) # we're going to update the median with the current image
    return (base - pmin)*0.98 + pmin

def linear_correction(array, med):
    '''apply a linear correction to the array by minimizing the residuals between array and med, using a linear scaling + offset'''
    m,b = determine_coefficients(array, med)
    return m * array + b

def determine_linear_coefficients(arr, med):
    '''returns the scaling m,b for mx+b that minimizes the residuals between arr and med'''
    def residual(vec):
        m,b = vec
        #return np.absolute(m*arr-b - med).sum() L1 norm
        return np.square(m*arr-b - med).sum()
    return minimize(residual, np.array([1.,0.]), bounds=[(0.,2.),(-2.,2.)], method='Nelder-Mead').x

def gamma_correction(array, med):
    A,g = determine_gamma_coefficients(array, med)
    print('gamma coefficients: A={}, gamma={}'.format(A,g))
    return A * np.power(array, g)

def determine_gamma_coefficients(arr, med):
    '''returns the scaling m,b for mx+b that minimizes the residuals between arr and med'''
    def residual(vec):
        A,g = vec
        #return np.absolute(m*arr-b - med).sum() L1 norm
        return np.absolute(A*np.power(arr,g) - med).sum()
    return minimize(residual, np.array([1.,1.]), bounds=[(0.,2.),(0.,2.)], method='Nelder-Mead').x

def efficient_mean(files, water_mask):
    '''iterate through files to limit RAM usage'''
    mean = np.ma.array(np.zeros_like(load_gdal(files[0])))
    count = np.zeros(shape=mean.shape).astype('uint16')
    wminv = np.invert(water_mask).astype('float')
    print('calculating mean over {} files...'.format(len(files)))
    for i, fil in enumerate(files):
        array = load_gdal(fil)
        array = np.ma.masked_where(water_mask, array)# apply water mask
        array.filled(0)
        print('loading {}/{} {} into stack...'.format(i, len(files), os.path.basename(fil)))
        mean = mean.data + array.data * wminv
        count = count + array.mask.astype('uint16')#array.count(axis=2)
        #print('current count mean: {}'.format(np.mean(count)))
    full_mean = mean.astype('float') / count.astype('float')
    mean_mask = np.invert(count.astype(bool)) # set mask to where there are no observations
    full_mean = np.ma.array(full_mean, mask=mean_mask)
    return full_mean

def get_corrections(stack, med):
    '''determine the proper correction coefficients over the given stack, compared to the stack's mean
    and return a list of the correction coefficients'''
    coeff = []
    for i in range(stack.shape[2]):
        s = stack[:,:,i]
        coeff.append(determine_coefficients(s, med))
    return coeff

def save(arr, filename, clim, date=None, overview=None):
    fig, ax = plt.subplots(figsize=(7,7))
    #rgba = np.dstack((arr,arr,arr,arr.mask))
    cmap = plt.cm.get_cmap('gist_gray')
    size = fig.get_size_inches()*fig.dpi # size of figure
    extent = 0, size[0], 0, size[1]
    im = ax.imshow(arr, cmap=cmap, clim=clim, extent=extent)
    # add the date
    if date:
        plt.text(10,10, date.strftime('%Y-%m-%d'), color='white', backgroundcolor='black', font='serif', fontweight='bold', fontsize='medium')
    if not overview is  None:
        im2 = plt.imshow(overview, interpolation='nearest', extent=extent)
    ax.axis('off')
    print('saving as {}'.format(filename))
    fig.savefig(filename, dpi=300, bbox_inches='tight', pad_inches=0.0, transparent=True, format='png', facecolor=(0.,0.,0.))
    plt.close(fig)

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
    print('loading {}'.format(filename))
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
