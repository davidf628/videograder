
import os, csv, util

#########################################################################
##
##  NOTES:
##
##    - If you have a student you want to exist in the database but is
##      not on the enrollment report from IR, you can add them in by
##      putting a '+' before that's students class name
##
##
##  Error Messages:
##    0 - No error
##   -1 - Error: students.txt not found
##   -2 - Error: file format error on class information
##    1 - Warning: file format error on a student record
##
#########################################################################

class Student:
    def __init__(self, fname, lname, sid, username, course, canwithdraw):
        self.fname = fname
        self.lname = lname
        self.sid = sid
        self.course = course
        self.username = username
        self.canwithdraw = canwithdraw
        self.videoswatched = {}

    def toList(self):

        if not self.canwithdraw:
            self.course = '+' + self.course
        list = [self.course]
        if '+' in self.course:
            self.course = self.course[1:]

        if len(self.lname) == 1:
            list.append(self.lname[0])
        else:
            names = ''
            for name in self.lname:
                names += name + ', '
            list.append(names[:-2])

        if len(self.fname) == 1:
            list.append(self.fname[0])
        else:
            names = ''
            for name in self.fname:
                names += name + ', '
            list.append(names[:-2])

        list.append(self.sid)
        list.append(self.username)

        return list

    def toString(self):
        return str(self.toList())

class Course:
    def __init__(self, videoset, name, termstart, termend, instructor, email):
        self.videoset = videoset
        self.name = name
        self.termstart = termstart
        self.termend = termend
        self.instructor = instructor
        self.email = email
        self.students = []

    def add_student(self, student):
        self.students.append(student)


##############################################################################
##
##  Used for testing and debugging purposes for this particular file
##

def test():

    import video

    config = util.load_config('config.toml')
    error, msg, video_data = video.load_video_data(config)

    error, msg, class_list = create_class_list(config, video_data)
    msg, class_list = refresh_students(config, class_list)

    print(msg)
    

################################################################################
##
##  Loads the class data and student data and combines into a single database
##

def create_class_list(config, video_data):

    error = 0
    msg = ''
    class_list = []
    student_list = []

    error, msg, class_list = loadClassData(config)
    if error < 0:
        return error, msg, class_list

    error, msg, student_list = loadStudentData(config)
    if error < 0:
        return error, msg, class_list

    # Once the class data and the student data has been loaded, the next
    # step is to traverse through the students and place them into their
    # appropriate classes.

    for student in student_list:
        found = False

        for course in class_list:

            if course.name == student.course:
                # Set up each student with a list of all the available videos for
                #   their class and set the grade to a default value
                videos = util.get_videos_in_playlist(course.videoset, video_data)

                for video in videos:
                    name = video['name']
                    student.videoswatched[name] = None

                course.students.append(student)
                found = True

        if not found:
            error = 1
            msg += f"WARNING: Student: {student.lname}, {student.fname} is in the class " \
                   f"{student.course} which cannot be located in classes.csv.\n"
    
    return error, msg, class_list


################################################################################
##
## Loads the class data from the classes.csv
##

def loadClassData(config):

        class_config = config['class_list']
        CLASS_FILE = class_config['filename']
        
        error = 0
        msg = ''
        classList = []

        # Collect the data about the courses
        if os.path.exists(CLASS_FILE):
            classfile = open(CLASS_FILE, encoding='ISO-8859-1')
            classfilereader = csv.reader(classfile)
            classdata = list(classfilereader)
            # Delete the first row of data which is just column titles
            classdata = classdata[1:]
        else:
            error = -1
            msg = 'Class database file "' + CLASS_FILE + '" not found. This should be located' \
                  ' in the same directory where the script is located.'
            return error, msg, classList

        for classrecord in classdata:
            
            videoset = classrecord[class_config['videoset_col']].lower().strip()
            course = classrecord[class_config['course_col']].lower().strip()
            termstart = classrecord[class_config['termstart_col']].lower().strip()
            termend = classrecord[class_config['termend_col']].lower().strip()
            instructor = classrecord[class_config['instructor_col']].lower().strip()

            # I don't always provide an email address
            if class_config['email_col'] >= len(classrecord):
                email = ''
            else:
                email = classrecord[class_config['email_col']].lower().strip()
            
            classList.append(Course(videoset, course, termstart, termend, instructor, email))           

        msg = 'Found ' + str(len(classList)) + ' class records.'
        return error, msg, classList


################################################################################
##
## Loads the student data from students.csv
##

def loadStudentData(config):

    student_config = config['student_list']
    STUDENT_FILE = student_config['filename']
    
    error = 0
    msg = ''
    studentList = []

    if os.path.exists(STUDENT_FILE):
        studentfile = open(STUDENT_FILE, encoding='ISO-8859-1')
        studentfilereader = csv.reader(studentfile)
        studentdata = list(studentfilereader)

    else:
        error = -1
        msg = 'Student database file "' + STUDENT_FILE + '" not found. This should be located' \
                ' in the same directory where the script is located.'
        return error, msg, studentList

    # Delete first row of data that is just column titles
    studentdata = studentdata[1:]

    for student in studentdata:
        canwithdraw = True

        # If a student needs to be permanant in the database, then the
        # student needs to have a '+' flag on the course name ensuring
        # that the system records them no matter what

        course = student[student_config['course_col']].lower().strip()
        if course.startswith('+'):
            course = course[1:]
            canwithdraw = False

        # The last name is a list that can contain multiple last names
        # per record
        
        name = student[student_config['lname_col']]

        if ',' in name:
            name = name.split(',')
            lname = [w.lower().strip() for w in name]
        else:
            lname = [name.lower().strip()]

        # The first name is a list that can contain multiple first
        # names per record

        name = student[student_config['fname_col']]

        if ',' in name:
            name = name.split(',')
            fname = [w.lower().strip() for w in name]
        else:
            fname = [name.lower().strip()]

        # Student ID Number - may possilby need to remove leading zeros
        # so that coversions with integers can happen; but I would prefer
        # making sure the SID is always a string and not an integer

        sid = student[student_config['sid_col']].lower().strip()

        # Convert the email address to a username. Also, account for student
        # email naming conventions vs. faculty email naming conventions
        
        username = util.get_username_from_email(student[student_config['email_col']].lower().strip())                 

        studentList.append(Student(fname, lname, sid, username, course, canwithdraw))


    msg = 'Found ' + str(len(studentList)) + ' student records.'
    return error, msg, studentList


###############################################################################
##
## Removes a student from the student database: classList
##

def deleteStudentRecord(student, classList):
    for course in classList:
        if student.course == course.name:
            index = -1
            for i in range(len(course.students)):
                if course.students[i].sid == student.sid:
                    index = i
            if index != -1:
                del course.students[index]

    return classList


###############################################################################
##
## Adds a new student to the student database (classList)
##

def addStudentRecord(student, classList):
    courseToFind = student.course
    for course in classList:
        if courseToFind == course.name:
            course.add_student(student)

    return classList


################################################################################
##
## Returns a list of the names of each class currently taught, for convenience
##

def getCurrentClasses(classList):
    courses = []
    for course in classList:
        courses.append(course.name)
    return courses


################################################################################
##
## Returns a list of the names of each student in the classes, mostly for
##   convenience and readability. Also sorts the students by last name before
##   writing out to disk
##

def getCurrentStudents(classList):
    students = []
    for course in classList:
        #sorted_course = sorted(course, key = lambda x: (x.students.lname, x.students.fname))
        for student in course.students:
            students.append(student)
    return students


################################################################################
##
## Goes through the student database looking for additions and withdrawals
##

def refresh_students(config, classList):
    
    message = ''

    enrollmentReportFromIR = load_student_data_from_extract(config)
    
    studentList = getCurrentStudents(classList)
    courses = getCurrentClasses(classList)

    if enrollmentReportFromIR:
        # Look through the new student list and see if there are any new adds
        for IRstudent in enrollmentReportFromIR:
            found = False
            for DBstudent in studentList:
                if (IRstudent.sid == DBstudent.sid) and (IRstudent.course == DBstudent.course):
                    found = True
            if (not found) and (IRstudent.course in courses):
                message += 'Student Added: ' + IRstudent.lname[0] + ', ' + IRstudent.fname[0] + ': ' + \
                           IRstudent.course + '\n'
                classList = addStudentRecord(IRstudent, classList)


        # Look through the old student list and see if anyone has withdrawn
        for student in studentList:
            if student.canwithdraw and not student_still_enrolled(student, enrollmentReportFromIR) and (student.course in courses):
                message += 'Withdraw: ' + student.lname[0] + ', ' + student.fname[0] + ': ' + student.course + '\n'
                classList = deleteStudentRecord(student, classList)

    # Save the changes to the student database
    writeStudentDataToDisk(config, classList)

    return message, classList


###############################################################################
##
##  Checks to see if a student is still enrolled in a class
##

def student_still_enrolled(student, enrollmentReportFromIR):

    found = False
    i = 0
    while (not found) and (i < len(enrollmentReportFromIR)):
        IRstudent = enrollmentReportFromIR[i]
        if(IRstudent.sid == student.sid) and (IRstudent.course == student.course):
            found = True
        i += 1

    return found


################################################################################
##
##  Saves the student database to disk.
##

def writeStudentDataToDisk(config, classList):

    studentList = getCurrentStudents(classList)
    studentlist_filename = config['student_list']['filename']

    with open(studentlist_filename, mode='w', newline='', encoding='ISO-8859-1') as student_file:
        student_writer = csv.writer(student_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Write header
        student_writer.writerow(['course', 'lastname', 'firstname', 'sid', 'email'])

        for student in studentList:
            student_writer.writerow(student.toList())


################################################################################
##
## Gets the extract file that is saved from IR and loads it into memory
##

def load_student_data_from_extract(config):

    extract_config = config['ir_extract']
    EXTRACT_FILE = extract_config['filename']

    # import the daily extract from IR
    if os.path.exists(EXTRACT_FILE):
        
        extractfile = open(EXTRACT_FILE, encoding='ISO-8859-1')
        extractfilereader = csv.reader(extractfile)
        extractdata = list(extractfilereader)

    # skip over the first row which is just column titles
    extractdata = extractdata[1:]

    student_data = []
    for record in extractdata:

        if len(record) != 0:
            course = record[extract_config['course_col']].lower().strip()
            sid = record[extract_config['sid_col']].lower().strip()
            stufirst = [record[extract_config['stufirst_col']].lower().strip()]
            stulast = [record[extract_config['stulast_col']].lower().strip()]
            username = util.get_username_from_email(record[extract_config['stuemail_col']].lower().strip())

            student_data.append(Student(stufirst, stulast, sid, username, course, True))

    return student_data


################################################################################
##
## Ensures there are no records in the class database that are duplicated.
##  Returns an error if there are any duplicated sections listed
##

def verify_class_data(config):

    error = 0
    msg = ""

    class_list_config = config['class_list']
    CLASS_FILE_NAME = class_list_config['filename']
    COURSE_TITLE_COL = class_list_config['course_col']

    # import the class data
    if os.path.exists(CLASS_FILE_NAME):
        
        file = open(CLASS_FILE_NAME, encoding='ISO-8859-1')
        filereader = csv.reader(file)
        classdata = list(filereader)

    # skip over the first row which is just column titles
    classdata = classdata[1:]

    # loop through all the classes and note any duplicates. If there are,
    # notify the user and halt execution

    while len(classdata) > 0:
        course_to_find = classdata.pop(0)
        course_name_to_find = course_to_find[COURSE_TITLE_COL]

        for course in classdata:
            if course_name_to_find == course[COURSE_TITLE_COL]:
                error = -1
                msg += f"{course_name_to_find} was found listed twice in the file {CLASS_FILE_NAME}. " \
                       f"This is not permitted and must be corrected before this script " \
                       f"can be run."

    return error, msg


################################################################################
##
## Ensures there are no records in the class database that are duplicated.
##  Deletes and student records that are duplicates (same SID and class)
##

def verify_student_data(config):

    error = 0
    msg = ""

    student_list_config = config['student_list']
    STUDENT_FILE_NAME = student_list_config['filename']
    SID = student_list_config['sid_col']
    COURSE = student_list_config['course_col']
    LNAME = student_list_config['lname_col']
    FNAME = student_list_config['fname_col']
    validated_students = [ ]

    # import the class data
    if os.path.exists(STUDENT_FILE_NAME):
        
        file = open(STUDENT_FILE_NAME, encoding='ISO-8859-1')
        filereader = csv.reader(file)
        studentdata = list(filereader)

    # skip over the first row which is just column titles
    studentdata = studentdata[1:]

    # loop through all the classes and note any duplicates. If there are,
    # notify the user and halt execution

    while len(studentdata) > 0:
        student_to_find = studentdata.pop(0)
        found = False

        for student in studentdata:
            if (student_to_find[COURSE] == student[COURSE]) and (student_to_find[SID] == student[SID]):
                found = True
                error = 1
                msg += f"Student: {student_to_find[LNAME]}, {student_to_find[FNAME]} was found listed " \
                       f"twice in the course {student_to_find[COURSE]} ==> " \
                       f"The duplicate record was removed.\n"
        
        if not found:
            validated_students.append(student_to_find)

    # Write the validated students to disk

    with open(STUDENT_FILE_NAME, mode='w', newline='', encoding='ISO-8859-1') as student_file:
        student_writer = csv.writer(student_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

        # Write header
        student_writer.writerow(['course', 'lastname', 'firstname', 'sid', 'email'])

        for student in validated_students:
            student_writer.writerow(student)

    return error, msg


###############################################################################
##                                                                 MAIN PROGRAM
###############################################################################

if __name__ == '__main__':
    test()
