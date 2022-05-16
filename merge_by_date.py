#!/usr/bin/env python3

'''merges files from the corrected folder into individual files by date'''

import os
import re
from datetime import datetime as dt
from tqdm import tqdm

IN_REGEX=r'^S1[AB].*?_([0-9]{8}).*.warped.vrt$' # regex for dates

INFOLDER='/products/warped'
OUTFOLDER='/products/merged_by_day'

def main():

    files = get_matching(INFOLDER)
    if not os.path.exists(OUTFOLDER):
        os.makedirs(OUTFOLDER)
    fil_dict = sort_into_dict(files)
    for date in tqdm(sorted(fil_dict.keys())):
        #if date.strftime('%Y-%m-%d') in BLACKLIST_DATES:
        #    continue
        fils = fil_dict.get(date)
        #print('generating scene for: {}'.format(date.strftime('%Y-%m-%d')))
        base = combine_files(fils, date)



def combine_files(fils, date):
    datestr = date.strftime('%Y%m%d')
    out_filename = 'S1_IW_SLC_HH_{}.merged.tif'.format(datestr)
    out_path = os.path.join(OUTFOLDER, out_filename)
    filenames = ' '.join(fils)
    #print('filenames: {}'.format(filenames))
    cmd = 'gdal_merge.py -o {} -of GTiff {}'.format(out_path, filenames)
    os.system(cmd)


def get_matching(infolder):
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
