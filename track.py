#!/usr/bin/env python3

'''
Retrieves Sentinel SLC files
'''

import re
import os
import json
import time
import pickle
import datetime
import dateutil.parser
import requests
import geopandas

ALLOWABLE=100 #number to allow on ASF's queue
S1_REGEX='^S1.*_([a-zA-Z0-9]{4}).+?$'
S1_PAIR_REGEX='^(S1[AB]_IW_SLC.*?)(S1[AB]_IW_SLC.*).nc$'

class granule:
    def __init__(self, name, gid, scenedate, status='unknown'):
        self.name = name
        self.gid = gid
        self.scenedate = scenedate
        self.status = status # should be either unknown, unsubmitted, submitted, or localized, failed, or blacklisted
        self.job_id = None
        self.object_type = 'granule'

    def __eq__(self, other):
        return type(self) == type(other) and self.gid == other.gid
    
    def __str__(self):
        return '{}'.format(self.name)


class granule_pair:
    def __init__(self, primary, secondary, status='unknown'):
        self.primary = primary
        self.secondary = secondary
        self.status = status # either unknown, unsubmitted, submitted, or localized, failed, or blacklisted
        self.job_id = None
        self.object_type = 'granule_pair'

    def __eq__(self, other):
        return type(self) == type(other) and self.primary == other.primary and self.secondary == other.secondary

    def __str__(self):
        return '{}-{}'.format(self.primary.gid, self.secondary.gid)
    


class track:
    def __init__(self, shapefile_path, polarization='HH', start_date=False, end_date=False, relativeorbit=False, autorift=False):
        self.output_dir = os.path.join('/products', 'RTC') # where to save output products
        self.json_file = os.path.join(self.output_dir, 'asf-results.json') # path for asf query file 
        self.tracking_file = os.path.join(self.output_dir, 'trackingfile.pkl') # file that stores all objects and submission status etc
        self.all_granules = [] # list containing all granules (initialized from the asf query)
        self.all_objects = [] # list containing all granules or granule pairs (for autorift)
        if os.path.exists(self.json_file) and not shapefile_path == False:
            os.remove(self.json_file) # remove any prior asf query (since we always want a fresh query)
        # set input variables and shapefile then update all_objects
        if not os.path.exists(shapefile_path):
            raise Exception('shapefile path does not exist: {}'.format(shapefile_path))
        self.shapefile_path = shapefile_path
        self.start_date = start_date
        self.end_date = end_date
        self.relativeorbit = relativeorbit
        # convert start & end dates to datetime objects
        if not start_date == False:
            self.start_date = dateutil.parser.parse(start_date).strftime("%Y-%m-%dT%H:%M:%S")
        if not end_date == False:
            self.end_date = dateutil.parser.parse(end_date).strftime("%Y-%m-%dT%H:%M:%S")
        self.polarization = polarization
        self.autorift = autorift # if True, then submit granule pairs for autorift jobs
        
        # initialize the lists
        self.query_asf() # fills self.all_granules with the query from asf
        self.load_pkl() # loads a pkl file (if it exists) into self.all_objects
        if autorift:
            self.generate_pairs() # generates a list of granule_pairs and saves it to self.all_objects
        else:
            self.all_objects = self.all_granules
        #self.refresh() # loads/reloads all the lists
        self.find_local_files()

    #def refresh(self):
    #    #if os.path.exists(self.tracking_file):
    #    #    self.load_pkl()
    #    # determine the files we have & correct submitted files
    #    self.find_local_files()
    
    def generate_pairs(self):
        '''determine all ordered pairs by going through self.all_granules. orders by date.'''
        self.all_pairs = []
        sorted_granules = sorted(self.all_granules, key=lambda x: x.scenedate)
        for first, second in zip(sorted_granules, sorted_granules[1:]):
           pair = granule_pair(first, second)
           self.all_objects.append(pair)

    def get_polygon(self):
        '''gets the polygon from an input shapefiles'''
        data = geopandas.read_file(self.shapefile_path)
        data = data.to_crs(epsg=4326) # epsg used by ASF
        coords = json.loads(data.exterior.to_json()).get('features',{})[0].get('geometry').get('coordinates')
        cstring = ','.join(['{} {}'.format(a,b) for a,b in coords])
        return 'polygon(({}))'.format(cstring)

    def query_asf(self):
        url = 'https://api.daac.asf.alaska.edu/services/search/param?'
        params = []
        # ADD YOUR QUERY PARAMETERS
        params.append('platform=S1')
        params.append('polarization={}'.format(self.polarization))
        params.append('processingLevel=SLC')
        params.append('intersectsWith={}'.format(self.get_polygon()))
        if not self.relativeorbit == False:
            params.append('relativeOrbit={}'.format(self.relativeorbit))
        if not self.start_date == False:
            params.append("start={}".format(self.start_date))
        if not self.end_date == False:
            params.append("end={}".format(self.end_date))
        params.append('output=json')
        query = url + '&'.join(params)
        #if not os.path.exists(self.output_dir):
        #    os.makedirs(self.output_dir)
        # save results to file
        response = requests.get(query).text
        with open(self.json_file, "w") as fout:
            fout.write(response)
        #return response
    #def parse_json(self):
        #with open(self.json_file, "r") as f:
        #    txt = f.read()
        json_obj = json.loads(response)[0]
        #print('found {} results!'.format(len(j)))
        #json_obj = response[0]
        for entry in json_obj:
            name = entry.get('granuleName')
            gid = name[-4:]
            scenedate = entry.get('sceneDate')
            scenedt = dateutil.parser.parse(scenedate).strftime("%Y-%m-%dT%H:%M:%S")
            gran = granule(name, gid, scenedt)
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

    def parse_time_from_name(self, name):
        DATE_REGEX = '^S1.*?(\d{8}T\d{6}).*$'
        #print('matching: {}'.format(name))
        dtstr = re.search(DATE_REGEX, name).group(1)
        return datetime.datetime.strptime(dtstr, '%Y%m%dT%H%M%S')

    def find_local_files(self):
        '''finds all the local files. if it finds any, it updates them to localized.'''
        # look for granules 
        local_files = [f for f in os.listdir(self.output_dir) if re.match(S1_REGEX, f) and not f.endswith('.zip') and not f.endswith('.nc')]
        for fil in local_files:
            #name = self.get_name(gid)
            #name = self.get_original_name(fil) 
            #gid = re.search(S1_REGEX, name).group(1)
            #scenedate = self.parse_time_from_name(name)
            #gran = granule(name, gid, scenedate, status='localized')
            gran = self.build_granule(fil, status='localized')
            if gran in self.all_granules:
                self.all_granules.remove(gran)
                self.all_granules.append(gran)
            if gran in self.all_objects:
                self.all_objects.remove(gran)
                self.all_objects.append(gran)
        self.save_pkl()
        # look for autorift jobs
        local_files = [f for f in os.listdir(self.output_dir) if re.match(S1_REGEX, f) and f.endswith('.nc')]
        for local_file in local_files:
            print('found completed autorift product: {}'.format(local_file))
            granule_pair = self.build_granule_pair(local_file, status='localized')
            if not granule_pair is None:
                print('found matching pair: {}'.format(granule_pair))
                self.all_objects.remove(granule_pair)
                self.all_objects.append(granule_pair)
        self.save_pkl()

    def build_granule(self, filename, status='unknown'):
        '''builds a granule object from a filename'''
        name = self.get_original_name(filename)
        gid = re.search(S1_REGEX, name).group(1)
        scenedate = self.parse_time_from_name(name)
        gran = granule(name, gid, scenedate, status=status)
        return gran

    def build_granule_pair(self, filename, status='unknown'):
        '''builds a granule pair object from a given localized .nc file'''
        if not re.match(S1_PAIR_REGEX, filename): 
            return # the file does not match properly
        primary = None
        secondary = None
        primary_str = re.search(S1_PAIR_REGEX, filename).group(1)
        secondary_str = re.search(S1_PAIR_REGEX, filename).group(2)
        # iterate through all_granules
        for granule in self.all_granules:
            if granule.name in primary_str:
                primary = granule
            if granule.name in secondary_str:
                secondary = granule
        if primary is None or secondary is None:
            return # No matching granules found
        return granule_pair(primary, secondary, status=status)


    def submit(self, objct, job_id=None):
        '''adds the granule to the submitted list and saves the pickle file'''
        #if objct in self.all_objects:
        #    self.all_objects.remove(objct) # remove the old object
        objct.status = 'submitted'
        if job_id:
            objct.job_id = job_id
        self.all_objects.remove(objct)
        self.all_objects.append(objct)
        self.save_pkl()

    def fail(self, objct):
        '''fails the job for the given object and saves the pickle file'''
        if objct in self.all_objects:
            self.all_objects.remove(objct) # remove the old object
        else:
            return # object wasn't in our list
        objct.status = 'failed'
        self.all_objects.append(objct)
        self.save_pkl()

    def localized(self, objct):
        '''sets the object as localized and saves the pickle file''' 
        objct.status = 'localized'
        if objct in self.all_objects:
            self.all_objects.remove(objct) # remove the old object
            self.all_objects.append(objct)
        self.save_pkl()

    def save_pkl(self):
        pickle.dump(self.all_objects, open(self.tracking_file, 'wb'))
        time.sleep(1)

    def load_pkl(self):
        '''loads the existing objects from the local pkl file'''
        if os.path.exists(self.tracking_file):
            objects = pickle.load(open(self.tracking_file, "rb" ))
            for objct in objects:
                if objct in self.all_objects:
                    self.all_objects.remove(objct)
                    self.all_objects.append(objct)
                # this could conflate queries
                if objct in self.all_granules:
                    self.all_granules.remove(objct)
                    self.all_granules.append(objct)


    def get_unsubmitted(self):
        '''returns a list containing all the unsubmitted granules/granule pairs'''
        return [g for g in self.all_objects if g.status in ['unsubmitted', 'unknown']]

    def get_submitted(self):
        '''returns a list containing all the submitted granules/granule pairs'''
        return self.get_status(status='submitted')

    def get_failed(self):
        '''returns a list contained all the objects with failed status'''
        return self.get_status(status='failed')
    
    def get_localized(self):
        return self.get_status(status='localized')

    def get_status(self, status=None):
        if status is None:
            return []
        return [g for g in self.all_objects if g.status == status]

    def get_submitted_job_names(self):
        #return ['job_thwaites_{}'.format(j.name[-4:]) for j in self.submitted_granules]
        return [j.job_id for j in self.get_submitted()]


    def submit_these(self):
        '''returns a list of granule names, if there are any allowable to be submitted'''
        unsubmitted = self.get_unsubmitted()
        submitted = self.get_submitted()
        submitted_count = len(submitted)
        if submitted_count >= ALLOWABLE:
            return []
        count = ALLOWABLE - submitted_count
        return unsubmitted[0:count]

    def print_status(self):
        submitted = self.get_submitted()
        unsubmitted = self.get_unsubmitted()
        localized = self.get_localized()
        failed = self.get_failed()
        print('::CURRENT TRACKING STATUS::')
        print(' unsubmitted: {}'.format(len(unsubmitted)))
        print(' submitted:   {}'.format(len(submitted)))
        print(' localized:   {}'.format(len(localized)))
        print(' failed:      {}'.format(len(failed)))
        print(' total:       {}'.format(len(self.all_objects)))

    def is_done(self):
        '''returns True if everything has been retrieved'''
        if len(self.get_submitted()) == 0 and len(self.get_unsubmitted()) == 0:
            return True
        return False

    def is_valid_name(self, name):
        '''returns True/False if the granule name is a valid granule to run over'''
        gid = name[-4:] 
        gran = granule(name, gid, None)
        if gran in self.all_granules:
            return True
        return False

if __name__ == '__main__':
    # load envs ('source config' should be run beforehand if not running from the script file)
    start = os.getenv('START_DATE')
    end = os.getenv('END_DATE')
    orbit = os.getenv('RELATIVE_ORBIT')
    shapefile_path = os.getenv('SHAPEFILE_PATH')
    shapefile_path = os.path.join('/data', os.path.basename(shapefile_path))
    autorift = bool(os.getenv('AUTORIFT'))
    t = track(shapefile_path, start_date=start, end_date=end, relativeorbit=orbit, autorift=autorift)
    t.print_status()
