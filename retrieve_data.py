#!/usr/bin/env python3

'''Submits job to ASF for RTC SLC and retrieves the data'''

import os
import time
import argparse
from datetime import datetime
from hyp3_sdk import HyP3
from hyp3_sdk import util
import track


def submit():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
    objs = t.submit_these()
    if len(objs) == 0:
        print('no objects currently able to be submitted')
        return
    else:
        print('submitting {} jobs...'.format(len(objs)))

    for obj in objs:
        obj.job_id = 'job_{}'.format(obj)
        print('submitting {} as {}'.format(obj, obj.job_id))
        if obj.object_type == 'granule':
            # submit rtc job
            #job = hyp3.submit_rtc_job(granule=gran, name=job_name, resolution=90, radiometry='gamma0', dem_name='copernicus', dem_matching=True)
            #job = hyp3.submit_rtc_job(granule=obj.gid, name=obj.job_id, dem_matching=True)
            job = hyp3.submit_rtc_job(obj.name, obj.job_id, dem_matching=True)
            obj.job = job[0]
            t.submit(obj)
            print('submitted job info: {}'.format(obj.job))
            print_job_info(obj.job)
        if obj.object_type == 'granule_pair':
            # submit autorift job
            autorift_job = hyp3.submit_autorift_job(obj.primary.name, obj.secondary.name, obj.job_id)
            obj.job = autorift_job[0]
            t.submit(obj)
            print('submitted job info: {}'.format(obj.job.job_id))
            print_job_info(obj.job)
    t.print_status()

def check_ASF():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
    submitted = t.get_submitted()
    #print('submitted granules: {}'.format(submitted))
    for obj in submitted:
        print('attempting to refresh job id: {}'.format(obj.job_id))
        ref = hyp3.refresh(obj.job)
        #status = ref.jobs[0].status_code
        status = ref.status_code
        print('job: {} : status_code: {}'.format(obj.job_id, status))
        if status == 'FAILED':
            print('job {} failed'.format(obj.job_id))
            obj.status = 'failed'
            t.fail(obj)
        if status == 'SUCCEEDED':
            print('job {} succeeded! downloading product.'.format(obj.job_id))
            print_job_info(obj.job)
            paths = ref.download_files(location='/products/RTC', create=True)
            obj.status = 'localized'
            #for path in paths:
            #    util.extract_zipped_product(path, delete=True)
            t.localized(obj)
    failed = t.get_failed()
    for obj in failed:
        print('failed job:')
        print(obj.job)
    #    ref = hyp3.refresh(obj.job)[0]
    #    print('HYP3.REFRESH DATA:')
    #    print_job_info(ref)

def check_and_retrieve():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
    submitted = t.get_submitted()
    for obj in submitted:
        job = obj.job
        print(job)
        job = hyp3.watch(job)
        job.download_files(location='/products/RTC', create=True)

    #jobs = hyp3.find_jobs()
    #jobs = t.get_submitted_job_names()
    #print('checking jobs...')
    ##succeeded_jobs = hyp3.find_jobs(status_code='SUCCEEDED')
    ##print(succeeded_jobs)
    #for jname in jobs:
    #    job = hyp3.find_jobs(status_code='SUCCEEDED', name=jname)
    #    if job:
    #        print('{} status is : {}'.format(jname, job))
    #        paths = job.download_files(location='/products/RTC/', create=True)
    #        for path in paths:
    #            util.extract_zipped_product(path, delete=True)

def just_download_available():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
        #job = hyp3.get_job_by_id(jname)
        #success = job.filter_jobs(succeeded=True, running=False, failed=False, include_expired=False)
        #print('success:'.format(success))
        # success.download_files(location='/products/RTC/', create=True)
        #print(job)

    #succeeded_jobs = jobs.filter_jobs(succeeded=True, running=False, failed=False, include_expired=False)
    succeeded_jobs = hyp3.find_jobs(status_code='SUCCEEDED')
    if len(succeeded_jobs) > 0:
        print('found completed jobs!')
        paths = succeeded_jobs.download_files(location='/products/RTC/', create=True)
        for path in paths:
            util.extract_zipped_product(path, delete=True)

def print_ASF():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
    suc = hyp3.find_jobs(status_code='SUCCEEDED')
    run = hyp3.find_jobs(status_code='RUNNING')
    fail = hyp3.find_jobs(status_code='FAILED')
    pend = hyp3.find_jobs(status_code='PENDING')
    print('::CURRENT ASF JOB STATUS::\n' \
            ' succeeded: {}\n' \
            ' running:   {}\n' \
            ' pending:   {}\n' \
            ' failed:    {}'.format(len(suc), len(run), len(pend), len(fail)))
    
    #for f in fail:
    #    print_job_info(f)

def print_job_info(obj):
    print('looking at job id: {}'.format(obj.job_id))
    for key, value in vars(obj).items():
        print('    {} : {}'.format(key, value))


def parser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    start = os.getenv('START_DATE')
    end = os.getenv('END_DATE')
    orbit = os.getenv('RELATIVE_ORBIT')
    shapefile_path = os.getenv('SHAPEFILE_PATH')
    shapefile_path = os.path.join('/data', os.path.basename(shapefile_path))
    autorift = bool(int(os.getenv('AUTORIFT')))
    parse = argparse.ArgumentParser(description="Generate time-series animation from input shapefile and time range")
    parse.add_argument("--shapefile", required=False, default=shapefile_path, help="input shapefile or kml file")
    parse.add_argument("--start", required=False, default=start, help="start date")
    parse.add_argument("--end", required=False, default=end, help="end date")
    parse.add_argument("--relativeorbit", required=False, default=orbit, help="relative orbit")
    parse.add_argument("--autorift", required=False, default=autorift, help="submit autorift jobs")
    return parse


if __name__ == '__main__':

    args = parser().parse_args()
    t = track.track(args.shapefile, start_date=args.start, end_date=args.end, relativeorbit=args.relativeorbit, autorift=args.autorift)
    t.print_status()
    submit()
    try:
        check_ASF()
    except:
        pass
    t.print_status()
    while not t.is_done():
        try:
            check_ASF()
        except:
            pass
        #t.print_status()
        submit()
        t.print_status()
        time.sleep(60)

    #    t.refresh()
    #    check_and_retrieve()
    #    #submit()
    #    t.print_status()
    #    print_ASF()
    #    time.sleep(120)

