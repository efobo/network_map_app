import sys
import os
import fnmatch

def getcreds(hostname):
        f = open(os.environ['HOME'] + '/.mikrotik', 'r')
        creds = f.readlines()
        f.close()

        for s in creds:
                l = s.split(':')
                if fnmatch.fnmatch(hostname, l[0]):
                        return {'username':str.strip(l[1]), 'password':str.strip(l[2])}

        raise Exception('Credentials for ' + hostname + ' not found');
