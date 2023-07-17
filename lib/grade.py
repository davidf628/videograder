import os, csv, glob, sqlite3
from datetime import datetime

import student, util

##########################################################################
##
##  Used for testing and debugging purposes in order to verify this module
##    is working properly
##

def test():

    import video
    config = util.load_config('config.toml')

    error, video_data = video.load_video_data(config)
    error, msg, class_list = student.create_class_list(config)
    class_list = load_instructor_gradebooks(config, class_list, video_data)


#############################################################################
##
##  Combines the data from the main database, any override information
##    provided by instructors and calculates the grades for each student
##    for each of the videos contained in a class
##

def process_video_grades(config, class_list, video_data):

    msg = ''
    db_config = config['database']
    video_config = config['video_data']
    db = sqlite3.connect(config['temp_db'])

    sql = '''SELECT * FROM view_data WHERE video LIKE ? AND starttime >= ? AND starttime <= ?'''

    # traverse through each course
    for course in class_list:

        msg += f"\nProcessing grades for: {course.name}\n"

        # Get a list of all videos that need to be evaluated for the class
        videos = util.get_videos_in_playlist(course.videoset, video_data)

        # Get the term start and term end dates for the class - specified in classes.csv
        startdate = course.termstart.split('/')
        termstartdate = datetime(int(startdate[2]), int(startdate[0]), int(startdate[1]), 0, 0, 0)

        enddate = course.termend.split('/')
        termenddate = datetime(int(enddate[2]), int(enddate[0]), int(enddate[1]), 23, 59, 59)

        # go through each video in the course playlist
        for video in videos:

            msg += f"Processing video: {video['name']}\n"

            # Get the video's due date if it exists
            duedates = util.get_student_by_username(course, 'duedates')
            if duedates != None:
                if video['name'] in duedates.videoswatched.keys():
                    duedate = duedates.videoswatched[video['name']]
                    date = duedate.split('/')
                    try:
                        termenddate = datetime(int(date[2]), int(date[0]), int(date[1]), 23, 59, 59)
                    except IndexError:
                        print(f"There is a due-date format error in {course.name}. Please check the d2l gradebook.")
                        raise SystemExit(-1)

            #### Query all the views for this video within the term dates
            #### then loop through it and compile grades
            cursor = db.cursor()
            cursor.execute(sql, (video['name'], termstartdate, termenddate))
            view_data = cursor.fetchall()

            # Get the total amount of time each student spent on the video
            for student in course.students:

                if student.username != 'duedates':
                    
                    # Retrieve all the views pertinent to this particular student
                    views = util.get_views_for_student(config, student, view_data)
                    
                    if len(views) > 0:
                    
                        # Get the total video run time
                        total_video_time = video['length']
                        
                        # Get the total play time reported by Yuja for all attempts
                        total_play_time = util.get_max_of_column(views, db_config['totalplaytime_col'])
                        total_play_pct = round(float(total_play_time) / float(total_video_time) * 100, 0)
                        
                        # Calculate an adjusted play time for this student - which
                        #   includes penalties for high speed playback
                        adjusted_play_time = 0

                        for view in views:
                            
                            playtime = 0
                            playfactor = view[db_config['factor_col']]
                            playpct = view[db_config['playpct_col']]
                            
                            # Watching videos at less than 1.5 speed is okay
                            if playfactor <= 1.618:
                                playtime = playpct
                                
                            # Watching videos between 1.5 and 4 speed incur a penalty
                            elif playfactor <= 4:
                                playtime = round(playpct / playfactor, 0)
                                
                            # Watching at greater than 4 speed get no credit
                            else:
                                playtime = 0
                            
                            adjusted_play_time += playtime

                        grade = min(adjusted_play_time, total_play_pct)

                        # Get the amount of time reported for this student to have watched already
                        if student.videoswatched.get(video['name']) != None:
                            override_play_time = student.videoswatched[video['name']]
                            grade = max(grade, override_play_time)
                        
                        if grade >= 95:
                            grade = 100
                            
                        student.videoswatched[video['name']] = int(grade)
                        msg += f"Student {student.lname[0]}, {student.fname[0].ljust(35,'.')} {grade}%\n"

                    #  If the student hasn't watched the video by the due date assign a grade of zero
                    elif datetime.now() > termenddate:
                        if student.videoswatched[video['name']] == None:
                            student.videoswatched[video['name']] = 0
                        
                        student.videoswatched[video['name']] = max(student.videoswatched[video['name']], 0)    
                        if student.videoswatched[video['name']] == 0:
                            msg += f"Student {student.lname[0]}, {student.fname[0].ljust(35,'.')} 0% --> Did not watch by the due date\n"
                        else:
                            msg += f"Student {student.lname[0]}, {student.fname[0].ljust(35,'.')} {student.videoswatched[video['name']]}%"

    return msg


###############################################################################
##
##  Each instructor has a .csv gradebook in the shared onedrive folder, and they
##    can do grade overrides by entering grades manually into the files stored
##    there. This function reads those gradebooks and stores the grades written
##    there in class_list in order to process these overrides.

def load_instructor_gradebooks(config, class_list, video_data):

    OVERRIDE_DIR = config['gradebook_shared_folder']

    #try:

    for course in class_list:

        # If OneDrive isn't synching, then it is possible that an instructor has edited a gradebook file, and those edits
        # would be missed. The following code will make sure all edits eventually get included

        gradebooks = glob.glob(os.path.join(OVERRIDE_DIR, course.instructor + '*.csv'))
        
        for gradebook_filename in gradebooks:
        
            # Read in the instructors current csv file - so that any updates are included
            if os.path.exists(gradebook_filename):
                gradebook_file = open(gradebook_filename, encoding='utf-8')
                csvReader = csv.reader(gradebook_file)
                gradebook_data = list(csvReader)

                # populate the data from the grade book into classList
                for student_record in gradebook_data:
                    username = student_record[1]

                    # if the student record is a list of due dates, process those
                    if username == 'duedates':
                        duedates = student.Student('', '', '0', 'duedates', course.name, False)

                        for i in range(2, len(student_record)):
                            date = student_record[i]
                            d2lname = gradebook_data[0][i]
                            video = get_video_by_d2lname(d2lname, course.videoset, video_data)
                            if video != None:
                                videoname = video['name']
                                if date == '':
                                    duedates.videoswatched[videoname] = course.termend
                                else:
                                    duedates.videoswatched[videoname] = date
                                
                        if util.get_student_by_username(course, 'duedates') == None:
                            course.students.append(duedates)
                            
                    # if the student record is an actual student process those
                    else:
                        for i in range(2, len(student_record)):
                            grade = student_record[i]
                            stu = util.get_student_by_username(course, username)

                            if util.is_number(grade) and stu != None:
                                grade = round(float(grade))
                                d2lname = gradebook_data[0][i]
                                try:
                                    video = get_video_by_d2lname(d2lname, course.videoset, video_data)
                                    videoname = video['name']
                                except TypeError:
                                    print(f'Could not find video {d2lname} in {course.name}')
                                    SystemExit(-1)

                                # if no grade has been assigned, go ahead and assign it
                                if stu.videoswatched.get(videoname) == None:
                                    stu.videoswatched[videoname] = grade

                                # if a higher grade is found on the instructors gradebook, use that
                                elif stu.videoswatched[videoname] <= grade:
                                    stu.videoswatched[videoname] = grade
                                
                                # if a zero appears in the instructors gradebook, use that
                                elif grade == 0:
                                    stu.videoswatched[videoname] = 0

        # Now that we've included all the possible extraneous gradebooks that result from synching errors, just delete the ones that
        # are no longer needed
        for gradebook in gradebooks:
            if os.path.join(OVERRIDE_DIR, course.instructor + '.csv') != gradebook:
                os.remove(gradebook)
    
    #except TypeError:
    #    print(gradebook_filename)
    #    SystemExit(-1)

    return class_list


###############################################################################
#
#  Takes all the information saved in classList and creates the individual
#  grade books that are emailed to the instructors.
#

def create_instructor_gradebooks(config, class_list, video_data):

    OUTPUTDIR = config['gradebook_shared_folder']
    
    # Make sure output directory exists
    if (not os.path.isdir(OUTPUTDIR)):
        os.mkdir(OUTPUTDIR)

    for course in class_list:
        data = []

        # Start putting the data into a 2D array structure
        output_filename = os.path.join(OUTPUTDIR, course.instructor + '.csv')
        videos = util.get_videos_in_playlist(course.videoset, video_data)

        # create the header row
        row = ['OrgDefinedID', 'Username']
        for video in videos:
            row.append(video['d2lname'])
        row.append('End-Of-Line Indicator')
        data.append(row)

        # Add each student to a new row in the output
        for student in course.students:
            if student.username == 'duedates':
                row = ['0', 'duedates']
            else:
                row = [util.remove_leading_zeros(student.sid), student.username]

            for video in videos:
                if video['name'] in student.videoswatched:
                    if student.videoswatched[video['name']] != -1:
                        row.append(student.videoswatched[video['name']])
                    else:
                        row.append('')
                else:
                    row.append('')

            row.append('#')
            data.append(row)

        output_file = open(output_filename, 'w', newline='')
        output_writer = csv.writer(output_file)
        output_writer.writerows(data)
        output_file.close()
    

###############################################################################
##
##  Gets the name of a video in yuja by it's equivalent name in d2l. A video
##    playlist/set must also be provided because there are a lot of videos named
##    the same within the d2l gradebook.
##

def get_video_by_d2lname(d2lname, playlist, video_data):

    videos_in_set = util.get_videos_in_playlist(playlist, video_data)

    for video in videos_in_set:
        if video['d2lname'] == d2lname:
            return video
        
    return None


###############################################################################
##                                                                 MAIN PROGRAM
###############################################################################

if __name__ == '__main__':
    test()
