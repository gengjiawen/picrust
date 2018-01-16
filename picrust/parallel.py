#!/usr/bin/env python

from __future__ import division

__author__ = "Morgan Langille"
__copyright__ = "Copyright 2015, The PICRUSt Project"
__credits__ = ["Morgan Langille"]
__license__ = "GPL"
__version__ = "1.1.3"
__maintainer__ = "Morgan Langille"
__email__ = "morgan.g.i.langille@gmail.com"
__status__ = "Development"


from os.path import exists
from subprocess import Popen, PIPE
from time import sleep
from itertools import izip_longest


def grouper(iterable, n, fillvalue=None):
        args = [iter(iterable)] * n
        return izip_longest(*args, fillvalue=fillvalue)


def submit_jobs(path_to_cluster_jobs, jobs_fp, job_prefix, num_jobs=100,
                delay=0):
    """ Submit the jobs to the queue using cluster_jobs.py
    """
    cmd = '%s -d %s -n %s -ms %s %s' % (path_to_cluster_jobs, delay, num_jobs,
                                        jobs_fp, job_prefix)
    stdout, stderr, return_value = system_call(cmd)
    if return_value != 0:
        msg = "\n\n*** Could not start parallel jobs. \n" +\
         "Command run was:\n %s\n" % cmd +\
         "Command returned exit status: %d\n" % return_value +\
         "Stdout:\n%s\nStderr\n%s\n" % (stdout,stderr)
        raise RuntimeError, msg

    # Leave these comments in as they're useful for debugging.
    # print 'Return value: %d\n' % return_value
    # print 'STDOUT: %s\n' % stdout
    # print 'STDERR: %s\n' % stderr


def system_call(cmd):
    """ Call cmd and return (stdout, stderr, return_value)"""
    proc = Popen(cmd,shell=True,universal_newlines=True,\
                 stdout=PIPE,stderr=PIPE)
    # communicate pulls all stdout/stderr from the PIPEs to
    # avoid blocking -- don't remove this line!
    stdout, stderr = proc.communicate()
    return_value = proc.returncode
    return stdout, stderr, return_value


def wait_for_output_files(files):
    ''' Function waits until all files exist in the filesystem'''
    # make a copy of the list
    waiting_files=list(files)

    # wait until nothing left in the list
    while(waiting_files):
        # wait 30 seconds between each check
        sleep(30)
        # check each file and keep ones that don't yet exist
        waiting_files=filter(lambda x: not exists(x),waiting_files)
