#!/usr/bin/env python3

## TODO:
##
## - Write code to clear the results of a bunch of videos on Yuja's website
## - Check to see if date written is time-zone specific
## - Move [ ERROR ] messages out of main program
## - Add ability to supress output to console
## - Rename student.lname and student.fname to lnames and fnames to indicate that its a list
## - Rename all video "sets" as "playlists"
## - Save times in videodata.csv as MM:SS so that it's easier to compare online
## - Come up with a method to prevent watching multiple videos simultaneously
## - blank lines are getting inserted at the end of the view data from yuja, how to prevent this?
## - Create an ability to award a single student extra time on a video
## - Verify that data is loaded from the instructor gradebooks and is persistent
##
##
## BUG REPORT:
##
## - The video for 120 2-3 on yuja's website is reported with two different
##     times, find out how to ensure to always retrieve the correct time
##     from the website

import os, sys, datetime, traceback, logging

sys.path.append(os.path.join('.', 'lib'))

import lib.util as util
import lib.video as video
import lib.student as student
import lib.yuja as yuja
import lib.grade as grade
import lib.database as db


def main(config, logger):

    starttime = datetime.datetime.now()

    # Make sure the reports database exists or else create it
    db.create_report_db(config)

    # Copy the database to a temporary location that is not affected by OneDrive
    util.create_temp_db(config)

    # Read the video data from the video database
    logAndDisplay(logger, 'Loading video data...', end='')
    error, msg, video_data = video.load_video_data(config)
    displayError(logger, error, msg)

    # Verify that the video data is all valid
    logAndDisplay(logger, 'Validating video data...', end='')
    error, msg, video_data = video.verify_video_data(config, video_data)
    displayError(logger, error, msg)

    # Verify that the student data is all valid
    logAndDisplay(logger, 'Validating student data...', end='')
    error, msg = student.verify_student_data(config)
    displayError(logger, error, msg)


    # Verify that the class data is all valid
    logAndDisplay(logger, 'Validating class data...', end='')
    error, msg = student.verify_class_data(config)
    displayError(logger, error, msg)

    # Load the class and student data from the databases
    logAndDisplay(logger, 'Loading Student and Class Data...', end='')
    error, msg, class_list = student.create_class_list(config, video_data)
    displayError(logger, error, msg)

    # Refresh the student database
    logAndDisplay(logger, 'Refreshing student database...', end='')
    msg, class_list = student.refresh_students(config, class_list)
    logAndDisplay(logger, '[ COMPLETE ]')
    logAndDisplay(logger, msg)

    if config['clear_online_data']:
        # Delete old view data from Yuja website, if requested
        logAndDisplay(logger, 'Deleting saved view data from Yuja website', end='')
        error, msg = yuja.delete_view_data_on_yuja(config, video_data)
        if error < 0:
            logAndDisplay(logger, '[ ERROR ]')
            performErrorExit(logger, msg)
        else:
            logAndDisplay(logger, '[ COMPLETE ]')
            logAndDisplay(logger, msg)       

    # Download the new reports from Yuja  
    logAndDisplay(logger, 'Downloading reports from Yuja website...', end='')
    error, msg = yuja.download_new_reports(config, video_data)
    if error < 0:
        logAndDisplay(logger, '[ ERROR ]')
        performErrorExit(logger, msg)
    else:
        logAndDisplay(logger, '[ COMPLETE ]')
        logAndDisplay(logger, msg)        

    # Load all the video results into the nightly_reports database
    db.load_views_into_db(config)

    setuptime = datetime.datetime.now()

    # Load all the instructor gradebooks into a database
    class_list = grade.load_instructor_gradebooks(config, class_list, video_data)

    # Compile the grades by comparing the nightly reports and instructor gradebooks
    msg = grade.process_video_grades(config, class_list, video_data)
    logAndDisplay(logger, msg)

    # Create the output CSV gradebook files
    grade.create_instructor_gradebooks(config, class_list, video_data)

    # Lastly, copy the temporary database back to the original directory so OneDrive can synch it
    util.delete_temp_db(config)

    logAndDisplay(logger, 'Program completed successfully.')

    endtime = datetime.datetime.now()

    elapsed = setuptime - starttime
    logAndDisplay(logger, '\nSetup Time: ' + str(elapsed))

    elapsed = endtime - setuptime
    logAndDisplay(logger, '\nProcessing Time: ' + str(elapsed))

    elapsed = endtime - starttime
    logAndDisplay(logger, '\nTotal Time: ' + str(elapsed))


#####################################################################
##
## If an error occurs during execution, make sure that the program ends
##   gently and notifies the admin through email
##

def performErrorExit(logger, msg):
        
    logAndDisplay(logger, '\nProgram exited with errors.')
    logAndDisplay(logger, '\nError message: ' + msg)
    logAndDisplay(logger, '\nSee log file for details.')
    logger.error(msg)
    sys.exit(1)


#####################################################################
##
## Prints error information to the console
##

def displayError(logger, error, msg):
    if error < 0:
        logAndDisplay(logger, '[ ERROR ]')
        performErrorExit(logger, msg)
    elif error > 0:
        logAndDisplay(logger, '[ WARNING ]')
        logAndDisplay(logger, msg)
    else:
        logAndDisplay(logger, '[ COMPLETE ]')


####################################################################
##
## Write output to both the main console and to the log file so that the
##   output is saved
##

def logAndDisplay(logger, msg, end='\n'):
     logger.info(msg)
     print(msg, end=end)


####################################################################
##                                                      MAIN PROGRAM
####################################################################

if __name__ == "__main__":

    config = util.load_config('config.toml')

    LOGFILENAME = config['logfile']

    # Start the log recording
    logging.basicConfig(filename=LOGFILENAME,level=logging.DEBUG)
    logging.FileHandler(LOGFILENAME, mode='w')
    logger = logging.getLogger()
        
    try:
        main(config, logger)

    except (KeyboardInterrupt, SystemExit):
        None

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        errormsg = traceback.format_exception(exc_type, exc_value, exc_traceback)
        d = datetime.datetime.now()
        logAndDisplay(logger, '\n' + d.strftime("%Y/%m/%d %H:%M:%S") + ': \n')
        for line in errormsg:
            logAndDisplay(logger, '\t--- ' + line)

