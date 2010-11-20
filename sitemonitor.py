#!/usr/bin/env python

# sample usage: checksites.py eriwen.com nixtutor.com yoursite.org

import pickle, os, sys, logging, time, urllib2, re
from optparse import OptionParser, OptionValueError
from smtplib import SMTP

def email_alert(toEmail, fromEmail, message, subject='You have an alert', useGmail=False, username='', password=''):
    toaddrs = toEmail
    if fromEmail != '':
        fromaddr = fromEmail
    else:
        fromaddr = toEmail

    if useGmail:
        if username and password:
            server = SMTP('smtp.gmail.com:587')
            server.starttls()
        else:
            raise OptionValueError('You must provide a username and password to use GMail')
    else:
        server = SMTP('localhost')

    if username != '' and password != '':
        server.login(username, password)

    server.sendmail(fromaddr, toaddrs, 'Subject: %s\r\n%s' % (subject,message))
    server.quit()

def get_site_status(url):
    try:
        status_code = urllib2.urlopen(url).code
        if status_code in (200,302):
            return 'up'
    except:
        pass
    return 'down'

def get_headers(url):
    '''Gets all headers from URL request and returns'''
    try:
        return urllib2.urlopen(url).info().headers
    except:
        return 'Headers unavailable'

def compare_site_status(prev_results):
    '''Report changed status based on previous results'''

    def is_status_changed(url):
        startTime = time.time()
        status = get_site_status(url)
        endTime = time.time()
        elapsedTime = endTime - startTime
        msg = "%s took %s" % (url,elapsedTime)
        logging.info(msg)

        friendly_status = '%s is %s' % (url, status)
        print friendly_status
        if url in prev_results and prev_results[url] != status:
            logging.warning(status)
            # Email status messages
            email_alert(str(get_headers(url)), friendly_status)
        prev_results[url] = status

    return is_status_changed

def is_internet_reachable():
    '''Checks Google then Yahoo just in case one is down'''
    if get_site_status('http://www.google.com') == 'down' and get_site_status('http://www.yahoo.com') == 'down':
        return False
    return True

def load_old_results(file_path):
    '''Attempts to load most recent results'''
    pickledata = {}
    if os.path.isfile(file_path):
        picklefile = open(file_path, 'rb')
        pickledata = pickle.load(picklefile)
        picklefile.close()
    return pickledata

def store_results(file_path, data):
    '''Pickles results to compare on next run'''
    output = open(file_path, 'wb')
    pickle.dump(data, output)
    output.close()


def normalize_url(url):
    '''If a url doesn't have a http/https prefix, add http://'''
    if not re.match('^http[s]?://', url):
        url = 'http://' + url
    return url

def get_urls_from_file(filename):
    try:
        return open(filename, 'r').read().split('\n')
    except:
        logging.error('Unable to read %s' % filename)
        return []

def get_command_line_options():
    '''Sets up optparse and command line options'''
    usage = "Usage: %prog [options] url"
    parser = OptionParser(usage=usage)
    parser.add_option("-t","--log-response-time", action="store_true",
            dest="logResponseTime",
            help="Turn on logging for response times")

    parser.add_option("-r","--alert-on-slow-response", action="store_true",
            help="Turn on alerts for response times")

    parser.add_option("-g","--use-gmail", action="store_true", dest="useGmail",
            help="Send email with Gmail.  Must also specify username and password")

    parser.add_option("-u","--smtp-username", dest="smtpUsername",
            help="Set the smtp username.")

    parser.add_option("-p","--smtp-password", dest="smtpPassword",
            help="Set the smtp password.")

    parser.add_option("-e","--from-email", dest="fromEmail",
            help="Set the from email, defaults to the email you are sending to.")

    parser.add_option("-f","--from-file", dest="fromFile",
            help="Import urls from a text file. Separated by newline.")

    return parser.parse_args()

def main():

    # Get argument flags and command options
    (options,args) = get_command_line_options()

    # Print out usage if no arguments are present
    if len(args) == 0 and options.fromFile == None:
        print 'Usage:'
        print "\tPlease specify a url like: www.google.com"
        print "\tNote: The http:// is not necessary"
        print 'More Help:'
        print "\tFor more help use the --help flag"

    # If the -f flag is set we get urls from a file, otherwise we get them from the command line.
    if options.fromFile:
        urls = get_urls_from_file(options.fromFile)
    else:
        urls = args

    urls = map(normalize_url, urls)

    # Change logging from WARNING to INFO when logResponseTime option is set
    # so we can log response times as well as status changes.
    if options.logResponseTime:
        logging.basicConfig(level=logging.INFO, filename='checksites.log',
                format='%(asctime)s %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
    else:
        logging.basicConfig(level=logging.WARNING, filename='checksites.log',
                format='%(asctime)s %(levelname)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')

    # Load previous data
    pickle_file = 'data.pkl'
    pickledata = load_old_results(pickle_file)

    # Check sites only if Internet is_available
    if is_internet_reachable():
        status_checker = compare_site_status(pickledata)
        map(status_checker, urls)
    else:
        logging.error('Either the world ended or we are not connected to the net.')

    # Store results in pickle file
    store_results(pickle_file, pickledata)

if __name__ == '__main__':
    # First arg is script name, skip it
    main()
