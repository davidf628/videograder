import os, sqlite3, csv #pytz
from datetime import datetime
from glob import glob
import util

db_schema = '''
    create table view_data (
        lname            text,
        fname            text,
        video            text,
        starttime        timestamp,
        endtime          timestamp,
        playlength       integer,
        playpct          integer,
        factor           real,
        totalplaytime    integer,
        UNIQUE (lname, fname, video, starttime, endtime, playlength, playpct, factor)
    );'''


################################################################
##
## Used for testing purposes to make sure everything in this file is
##   working properly.
##

def test():

    config = util.load_config('config.toml')
        
    create_report_db(config)

    util.create_tempdb(config)
    load_views_into_db(config)
    util.delete_tempdb(config)


#################################################################
##
## Creates a new database to save all the watch data found nightly on yuja.
##   This just makes a permanent storage location for all the saved watch data
##

def create_report_db(config):

    report_db = config['reports_db']
    db_exists = os.path.exists(report_db)
        
    if not db_exists:
        print('Nightly Report Database does not exist, now creating...', end='')
        conn = sqlite3.connect(report_db)
        conn.executescript(db_schema)
        print('[ COMPLETE ]')
        conn.close()


##################################################################
##
##  Loads the new nightly views from the files saved from yuja's website into
##    the main database for permanent storage and easy retrieval when grading
##

def load_views_into_db(config):

    view_config = config['view_data']

    insert_sql = '''INSERT OR REPLACE INTO view_data values(?, ?, ?, ?, ?, ?, ?, ?, ?)'''

    # Get a list of all the reports in the report download directory
    folder_path = os.path.join(config['report_folder'], '*_report.csv')
    reportlist = glob(folder_path)

    # Open up the nightly report database for writing
    db = sqlite3.connect(config['temp_db'], detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor = db.cursor()

    # Loop through all the files saved from yuja
    for filename in reportlist:
        
        fp = open(filename, encoding = 'utf-8')
        filereader = csv.reader(fp)
        filedata = list(filereader)
        filedata = filedata[1:] # skip over column headers

        for view in filedata:
            
            if view != []:

                lname = view[view_config['lname_col']].strip().lower()
                fname = view[view_config['fname_col']].strip().lower()
                video = view[view_config['videoname_col']].strip().lower()
                starttime = datetime.strptime(view[view_config['starttime_col']], '%Y-%m-%d %H:%M:%S')
                endtime = datetime.strptime(view[view_config['endtime_col']], '%Y-%m-%d %H:%M:%S')
                playlength = int(view[view_config['playlength_col']])
                playpct = round(int(playlength) / int(view[view_config['videolength_col']]) * 100)
                timediff = (endtime - starttime).total_seconds()
                if timediff != 0:
                    factor = playlength / timediff
                else:
                    factor = 1.0
                totalplaytime = int(view[view_config['totalplaytime_col']])
                
                cursor.execute(insert_sql, (lname, fname, video, starttime, endtime, playlength, playpct, factor, totalplaytime))
        
        fp.close()

    # Close the datatbase
    db.commit()
    db.close()

# def getViewTime (start, end):

#     starttime = getDateTime(start)
#     endtime = getDateTime(end)

#     return (endtime - starttime).seconds

def get_date(timestamp):

    timedateinfo = timestamp.split(' ')
    datestr = timedateinfo[0]
    # timestr = timedateinfo[1]
    
    # dateinfo = datestr.split('-')
    # timeinfo = timestr.split(':')

    # year = int(dateinfo[0])
    # month = int(dateinfo[1])
    # day = int(dateinfo[2])

    # hour = int(timeinfo[0]) % 12
    # if 'P' in timedateinfo[2]:
    #     hour += 12
    # minute = int(timeinfo[1])
    # second = int(timeinfo[2])                

    # # Adjust for the time zone and daylight savings (GMT to EST is a difference of 5 hours)

    # est = pytz.timezone("US/Eastern")
    # adjdate = datetime.datetime(year, month, day, hour, minute, second)
    # dstoffset = est.localize(adjdate).dst()
    # tzoffset = datetime.timedelta(hours = -5)
    
    # return adjdate + tzoffset + dstoffset
    return datestr

##################################################
##                                    Main Program
##################################################

if __name__ == "__main__":
    test()
