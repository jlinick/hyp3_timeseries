#!/usr/bin/env python3

'''
Retrieves Sentinel SLC files
'''

import re
import os
import json
import pickle
import requests

ALLOWABLE=40 #number to allow on ASF's queue
S1_REGEX='^S1.*_([a-zA-Z0-9]{4}).+?$'

class granule:
    def __init__(self, name, gid):
        self.name = name
        self.gid = gid

    def __eq__(self, other):
        return self.gid == other.gid

class track:
    def __init__(self):
        self.refresh() # loads/reloads all the lists

    def refresh(self):
        self.output_dir = os.path.join('/products', 'RTC')
        self.json_file = os.path.join(self.output_dir, 'asf-results.json')
        self.submitted_file = os.path.join(self.output_dir, 'submitted.pkl')
        self.submitted_granules = []
        if os.path.exists(self.submitted_file):
            self.load_pkl()
        self.all_granules = []
        self.local_granules = []
        if not os.path.exists(self.json_file):
            self.query_asf()
        # parse out all the files that we want from the asf query
        self.parse_json()
        # determine the files we have & correct submitted files
        self.find_local_files()

    def query_asf(self):

        #'&intersectsWith=point(-106.2082 -75.3699)' \
        #'&intersectsWith=point(-107.07 -75.52)' \

        query = 'https://api.daac.asf.alaska.edu/services/search/param?' \
                'platform=S1&polarization=HH' \
                '&processingLevel=SLC' \
                '&relativeOrbit=7' \
                '&intersectsWith=polygon((-103.670842344576 -74.4177148534973,-106.231146758566 -76.8020969230241,-114.223083850336 -76.0681200296965,-110.706357839052 -73.8378293132052,-103.670842344576 -74.4177148534973))' \
                '&start=2015-01-01T00:00:00' \
                '&end=2020-09-01T00:00:00' \
                '&output=json'
        print(query)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        # save results to file
        response = requests.get(query).text
        with open(self.json_file, "w") as fout:
            fout.write(response)

    def parse_json(self):
        with open(self.json_file, "r") as f:
            txt = f.read()
        json_obj = json.loads(txt)[0]
        #print('found {} results!'.format(len(j)))
        for entry in json_obj:
            name = entry.get('granuleName')
            gid = name[-4:]
            gran = granule(name, gid)
            if gran not in self.all_granules:
                self.all_granules.append(gran)

    def get_name(self, gid):
        '''attempts to return the granule name for the id'''
        for gran in self.all_granules:
            if gran.gid == gid:
                return gran.name
        return None

    def get_original_name(self, fil):
        '''looks at the log file to determine the original file name'''
        path = '/products/RTC/{}/{}.log'.format(fil,fil)
        LOG_REGEX = "^.*SAFE directory[ ]*: (S1.*\.SAFE)"
        for line in open(path, 'r'):
            if re.match(LOG_REGEX, line): 
                return re.search(LOG_REGEX, line).group(1)

    def find_local_files(self):
        '''finds all the local files'''
        local_files = [f for f in os.listdir(self.output_dir) if re.match(S1_REGEX, f) and not f.endswith('.zip')]
        for fil in local_files:
            #name = self.get_name(gid)
            name = self.get_original_name(fil) 
            gid = re.search(S1_REGEX, name).group(1)
            gran = granule(name, gid)
            #print('name: {}, gid: {}'.format(name, gid))
            if gran not in self.local_granules and gran in self.all_granules:
                self.local_granules.append(gran)
                # now remove from submitted
                if gran in self.submitted_granules:
                    self.submitted_granules.remove(gran)
                    self.save_pkl()

    
    def submit(self, name):
        '''adds the granule to the submitted list and saves the pickle file'''
        g = granule(name, name[-4:])
        self.submitted_granules.append(g)
        self.save_pkl()

    def save_pkl(self):
        pickle.dump(self.submitted_granules, open(self.submitted_file, 'wb'))

    def load_pkl(self):
        '''loads the submitted files from the local pkl file'''
        self.submitted_granules = pickle.load(open(self.submitted_file, "rb" ) )

    def get_unsubmitted(self):
        '''returns a list of the names of all the unsubmitted granules'''
        return [g for g in self.all_granules if g not in self.submitted_granules and g not in self.local_granules]

    def get_submitted_job_names(self):
        return ['job_thwaites_{}'.format(j.name[-4:]) for j in self.submitted_granules]

    def submit_these(self):
        '''returns a list of granule names, if there are any allowable to be submitted'''
        submitted_count = len(self.submitted_granules)
        if submitted_count >= ALLOWABLE:
            return []
        count = ALLOWABLE - submitted_count
        grans = self.get_unsubmitted()[0:count]
        return [g.name for g in grans]

    def print_status(self):
        n_all = len(self.all_granules)
        n_out = len(self.submitted_granules)
        n_uns = len(self.get_unsubmitted())
        n_local = len(self.local_granules)
        print('::LOCAL::')
        print(' submitted: {}'.format(n_out))
        print(' unsubmitted: {}'.format(n_uns))
        print(' retrieved: {}'.format(n_local))
        print(' total:     {}'.format(n_all))

    def is_done(self):
        '''returns True if everything has been retrieved'''
        if len(self.local_granules) >= len(self.all_granules):
            return True
        return False

    def is_valid_name(self, name):
        '''returns True/False if the granule name is a valid granule to run over'''
        gid = name[-4:] 
        gran = granule(name, gid)
        if gran in self.all_granules:
            return True
        return False

if __name__ == '__main__':
    t = track()
    t.print_status()
