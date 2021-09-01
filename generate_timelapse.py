#!/usr/bin/env python3

'''generates the animation from the individual merged file outputs'''


import os
import re
import argparse
import numpy as np
from datetime import datetime as dt
from datetime import timedelta
import matplotlib.pyplot as plt
from PIL import Image
from osgeo import gdal
import shutil

DIRECTORY_REGEX=r'^[0-9]{8}$'
INFOLDER='/products/matched'
OUTFOLDER='/products/timelapse'
IN_REGEX=r'^S1-([0-9]{8}).matched.png$'
N_DAYS=1 # a frame every n days (>1)


class timelapse():

    def __init__(self):
        self.dates = {} # dict that gives a filename from the date obj
        if not os.path.exists(OUTFOLDER):
            os.makedirs(OUTFOLDER)

    def build(self):
        '''generate the timelapse'''
        self.fils = self.get_input_files()
        for i, fil in enumerate(self.fils):
            inpath = os.path.join(INFOLDER, fil)
            outpath = os.path.join(OUTFOLDER, 's1-{:05d}.png'.format(i))
            print(inpath, outpath)
            shutil.copy(inpath, outpath)

        # generate mp4 from images
        cmd = 'ffmpeg -y -r 20 -i "{}/s1-%05d.png" -crf 22 -preset slow -c:a ac3 -vf "scale=3840:-1" {}/s1-backscatter_timeseries.mp4'.format(OUTFOLDER,OUTFOLDER)
        os.system(cmd)
        print(cmd)

    def combine_date(self, date):
        '''combine files for the given date and save the output'''
        fils = self.dates.get(date, [])
        if len(fils) == 0:
            return self.base
        return self.combine(fils)

    def fill_dates(self):
        '''fill self.dates with {date: filename}'''
        for fil in self.fils:
            date = get_date(fil)
            if date not in self.dates:
                self.dates[date] = list()
            self.dates[date].extend([fil])

    def load(self, fil):
        ds = gdal.Open(fil)
        arr = np.ma.masked_less(np.ma.array(ds.GetRasterBand(1).ReadAsArray()),1)
        return arr

    def save(self, arr, path):
        fig, ax = plt.subplots(figsize=(11,7))
        #rgba = np.dstack((arr,arr,arr,arr.mask))
        im = ax.imshow(arr, cmap='gist_gray')
        ax.axis('off')
        #print('saving as {}'.format(path))
        fig.savefig(path, dpi=300, bbox_inches='tight', pad_inches=0.0, transparent=True, format='png')
        plt.close()

    def combine(self, fil_list):
        '''combine multiple images into a single array (if needed). returns the combined array'''
        stack = np.ma.dstack([self.load(os.path.join(INFOLDER,fil)) for fil in fil_list])
        # get the mean of the stack
        med = np.ma.mean(stack, axis=2)
        # combine it with the base
        combined = np.ma.filled(med, fill_value=self.base)
        self.base = combined
        return combined

    def get_input_files(self):
        '''returns all input files'''
        return sorted([f for f in os.listdir(INFOLDER) if re.match(IN_REGEX,f)], key=get_date)

def get_date(path):
    '''parses the datetime from the path name'''
    filename = os.path.basename(path)
    datestr = re.search(IN_REGEX, filename).group(1)
    return dt.strptime(datestr, '%Y%m%d')


if __name__ == '__main__':
    t = timelapse()
    t.build()
