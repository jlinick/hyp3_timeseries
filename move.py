#!/usr/bin/env python3

'''moves files from /products/testing (future /products/RTC) to /products/corrected and rename them properly'''

import os
import re
import shutil
import track

S1_REGEX='^S1.*_([a-zA-Z0-9]{4}).+?$'
TIFF_REGEX= '^S1.*_HH.tif$'

class group:
    def __init__(self):
        self.inpath = '/products/RTC'
        self.outpath = '/products/corrected'
        self.t = track.track()
        if not os.path.exists(self.outpath):
            os.makedirs(self.outpath)

    def get_original_name(self, fil):
        '''looks at the log file to determine the original file name'''
        path = os.path.join(self.inpath, '{}/{}.log'.format(fil,fil))
        if not os.path.exists(path):
            return
        LOG_REGEX = "^.*SAFE directory[ ]*: (S1.*\.SAFE)"
        for line in open(path, 'r'):
            if re.match(LOG_REGEX, line):
                return re.search(LOG_REGEX, line).group(1)

    def get_tiff_filename(self, fdir):
        dirfiles = os.listdir(fdir)
        for fil in dirfiles:
            if re.match(TIFF_REGEX, fil):
                return fil

    def copy_tiffs(self):
        '''finds all the local files'''
        local_files = [f for f in os.listdir(self.inpath) if re.match(S1_REGEX, f) and not f.endswith('.zip')]
        for fil in local_files:
            fdir = os.path.join(self.inpath, fil)
            if not os.path.isdir(fdir):
                return
            # determine which file to copy and the proper name
            basename = self.get_original_name(fil).replace('.SAFE', '')
            if not self.t.is_valid_name(basename):
                print('{} is not in the query... skipping!'.format(basename))
                continue
            tiff_fn = self.get_tiff_filename(fdir)
            outfname = '{}.corrected.vrt'.format(basename)
            frompath = os.path.join(fdir, tiff_fn)
            topath = os.path.join(self.outpath, outfname)
            #if not os.path.exists(topath):
            #    print('copying {} to {}'.format(frompath, topath))
            #    shutil.copy(frompath, topath)
            print('building {}'.format(outfname))
            cmd = 'gdalbuildvrt -resolution highest {} {}'.format(topath, frompath)
            os.system(cmd)

if __name__ == '__main__':
    g = group()
    g.copy_tiffs()

