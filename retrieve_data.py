#!/usr/bin/env python3

'''Submits job to ASF for RTC SLC and retrieves the data'''

import time
from datetime import datetime
from hyp3_sdk import HyP3
from hyp3_sdk import util
import track



t = track.track()

def submit():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
    granule_names = t.submit_these()
    if len(granule_names) == 0:
        print('nothing allowable to submit...')
    else:
        print('submitting {} jobs...'.format(len(granule_names)))

    for gran in granule_names:
        job_name = 'job_thwaites_{}'.format(gran[-4:])
        print('submitting {} as {}'.format(gran, job_name))
        #job = hyp3.submit_rtc_job(granule=gran, name=job_name, resolution=90, radiometry='gamma0', dem_name='copernicus', dem_matching=True)
        job = hyp3.submit_rtc_job(granule=gran, name=job_name, dem_matching=True)
        t.submit(gran)
        t.print_status()
        print('submitted job info: {}'.format(job))
        print('submitted job: {}'.format(job_name))

def check_and_retrieve():
    hyp3 = HyP3(api_url='https://hyp3-api.asf.alaska.edu')
    #jobs = hyp3.find_jobs()
    jobs = t.get_submitted_job_names()
    print('checking jobs...')
    #succeeded_jobs = hyp3.find_jobs(status_code='SUCCEEDED')
    #print(succeeded_jobs)
    for jname in jobs:
        job = hyp3.find_jobs(status_code='SUCCEEDED', name=jname)
        if job:
            print('{} status is : {}'.format(jname, job))
            paths = job.download_files(location='/products/RTC/', create=True)
            for path in paths:
                util.extract_zipped_product(path, delete=True)

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
    print('::ASF::\n succeeded: {}\n' \
                   ' running:   {}\n' \
                   ' pending:   {}\n' \
                   ' failed:    {}'.format(len(suc), len(run), len(pend), len(fail)))


if __name__ == '__main__':

    #t.print_status()
    #print_ASF()
    #just_download_available()
    #t.print_status()
    #print_ASF()

    while not t.is_done():
        t.refresh()
        check_and_retrieve()
        submit()
        t.refresh()
        t.print_status()
        print_ASF()
        time.sleep(120)

