#!/usr/bin/env python3
'''
Processess the autorift netcdf files so they can be generated into h5 files or animations
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

S1_OBJ_REGEX='^(S1[AB].*_S1[AB].*.nc)$'
S1_PAIR_REGEX='^(S1[AB]_IW_SLC.*?)(S1[AB]_IW_SLC.*).nc$'

class autorift_product:
    def __init__(self, file_path):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.basename = self.filename.rstrip('nc').rstrip('.')
        self.fill_params()

    def fill_params(self):
        primary_str = re.search(S1_PAIR_REGEX, self.filename).group(1)
        primary_granule_name = primary_str[:67]
        self.primary_datetime = self.parse_time_from_name(primary_granule_name)
        self.primary_date = self.primary_datetime.date()
        secondary_str = re.search(S1_PAIR_REGEX, self.filename).group(2)
        secondary_granule_name = secondary_str[:67]
        self.secondary_datetime = self.parse_time_from_name(secondary_granule_name)
        self.secondary_date = self.secondary_datetime.date()

    def parse_time_from_name(self, name):
        DATE_REGEX = '^S1.*?(\d{8}T\d{6}).*$'
        #print('matching: {}'.format(name))
        dtstr = re.search(DATE_REGEX, name).group(1)
        return datetime.datetime.strptime(dtstr, '%Y%m%dT%H%M%S')
    
    def export_to_geotiff(self, output_dir):
        '''save the velocity, vx, and vy products to the output dir'''
        cstr = 'gdal_translate NETCDF:"{}":{} {}{}'
        # generate velocity, vx, and vy geotiffs
        base_path = os.path.join(output_dir, self.__str__())
        cmd = cstr.format(self.file_path, 'v', base_path, '.v.tif')
        os.system(cmd)
        cmd = cstr.format(self.file_path, 'vx', base_path, '.vx.tif')
        os.system(cmd)
        cmd = cstr.format(self.file_path, 'vy', base_path, '.vy.tif')
        os.system(cmd)
        cmd = cstr.format(self.file_path, 'v_error', base_path, '.v_error.tif')
        os.system(cmd)

    def __eq__(self, other):
        return type(self) == type(other) and self.primary_datetime == other.primary_datetime and self.secondary_datetime == other.secondary_datetime

    def __str__(self):
        return 'S1AR_{}-{}'.format(self.primary_date, self.secondary_date)

    def __ge__(self, other):
        return self.primary_datetime >= other.primary_datetime

    def __gt__(self, other):
        return self.primary_datetime > other.primary_datetime

    def __le__(self, other):
        return self.primary_datetime <= other.primary_datetime

    def __lt__(self, other):
        return self.primary_datetime < other.primary_datetime

    def connected(self, other):
        if self.primary_date == other.secondary_date:
            return True
        if other.primary_date == self.secondary_date:
            return True
        return False

    def overlap(self, other):
        '''if <0 there is overlap, 0=bookended, >0 is the distance between the two in days'''
        delta = min(self.primary_date, other.primary_date) - max(self.secondary_date, other.secondary_date)
        return delta.total_seconds() / 86400

class sorter:
    '''does things like sort the jobs and check to see if they're fully connected'''
    def __init__(self, all_objects):
        self.all_objects = all_objects # list of autorift product objects
        self.sorted_objects = self.sort()

    def sort(self):
        '''returns a list of autorift objects sorted by date'''
        return sorted(self.all_objects, key=lambda x: x.primary_date)

    def is_connected(self, obj_list):
        '''returns True/False if the object list contains all connected pairs'''
        for first, second in zip(obj_list, obj_list[1:]):
            if not first.connected(second):
                return False
        return True

    def get_best_list(self):
        '''returns a list of autorift objects that's been sorted by date'''
        # if they're all connected just return the sorted list
        if self.is_connected(self.sorted_objects):
            return self.sorted_objects
        # I CAN DO THIS THE SMART/ELEGANT/MORE ROBUST WAY LATER
        #best_list = []
        #l = len(self.sorted_objects)
        #for i, obj in enumerate(self.sorted_objects[:-1]:
        return self.sorted_objects

    def print_missing_connections(self):
        '''prints the gaps in the products'''
        for first, second in zip(self.sorted_objects, self.sorted_objects[1:]):
            if not first.connected(second):
                print('{} to {} is not connected! (separation: {} days)'.format(first, second, first.overlap(second)))

    def print_info(self):
        print('::SORTED PAIRS::')
        for obj in self.sorted_objects:
            print(obj)
        if self.is_connected(self.sorted_objects):
            print('::OBJECTS ARE CONNECTED::')
        else:
            print('::OBJECTS ARE NOT CONNECTED::')
            self.print_missing_connections()

def main():
    input_dir = '/products/RTC'
    output_dir = '/products/AUTORIFT'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # look for autorift files
    local_files = [f for f in os.listdir(input_dir) if re.match(S1_PAIR_REGEX, f) and f.endswith('.nc')]
    objs = []
    for local_file in local_files:
        print('found completed autorift product: {}'.format(local_file))
        local_path = os.path.join(input_dir, local_file)
        prod = autorift_product(local_path)
        print(prod)
        if not prod in objs:
            objs.append(prod)
    s = sorter(objs)
    objs = s.get_best_list()
    s.print_info()
    # save to geotiff
    for obj in objs:
        obj.export_to_geotiff(output_dir)


if __name__ == '__main__':
    start = os.getenv('START_DATE')
    end = os.getenv('END_DATE')
    orbit = os.getenv('RELATIVE_ORBIT')
    shapefile_path = os.getenv('SHAPEFILE_PATH')
    shapefile_path = os.path.join('/data', os.path.basename(shapefile_path))
    autorift = bool(os.getenv('AUTORIFT'))
    main()
