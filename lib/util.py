import os, tomli, shutil

#######################################################################
##
##  Loads the main configuration data into memory for use throughout
##    the program
##

def load_config(config_filename):

    if os.path.exists(config_filename):
        with open(config_filename, 'rb') as f:
            config = tomli.load(f)

        # Set the current working directory to something relative to this program
        config['rootdir'] = os.path.dirname(os.path.realpath(config_filename))
        os.chdir(config['rootdir'])

        config['homedir'] = os.path.expanduser('~')
        config['reports_db'] = os.path.join(config['rootdir'], config['database']['filename'])
        config['temp_db'] = os.path.join(config['homedir'], config['database']['filename'])

        # Locate the correct folder for one drive and set up the folder to write
        #   the instructor gradebooks to for sharing

        onedrive_path = locate_path(config['onedrive'])
        if onedrive_path == False:
            raise SystemExit(f"OneDrive folder location could not be found. Please check the config.toml file.")
        else:
            config['gradebook_shared_folder'] = get_path(onedrive_path, config['gradebook_folder'])

        return config    

    else:
        raise SystemExit(f'Configuration file "{config_filename}" not located.')


##################################################################################
##
##  Creates a copy of the current database in a folder that is not synched to
##    OneDrive because the number of writes required makes OneDrive unable to keep
##    up and ultimately fails.
##

def create_temp_db(config):
    if os.path.exists(config['reports_db']):
        shutil.copy2(config['reports_db'], config['temp_db'])
        if not os.path.exists(config['temp_db']):
            raise IOError("Could not copy database to home directory.")


###############################################################################
##
##  Copies the temporary database back to the original script folder so that
##    it can synch through OneDrive. Then deletes the temporary database.
##

def delete_temp_db(config):
    shutil.copy2(config['temp_db'], config['reports_db'])
    os.remove(config['temp_db'])


###############################################################################
##
##  Takes an array of folder locations and tries to figure out which one is
##    valid for the current system. If none are, then an error is flagged.
##

def locate_path(path):

    if isinstance(path, str):
        path = [ path ]

    for loc in path:
        if os.path.isdir(loc):
            return loc
    return False


###########################################################################
##
##  Combines a known path with a given filename or folder and creates a
##    new absolute path to that location.
##

def get_path(path, filename):

    path_parts = filename.split('/')
    filepath = os.path.join(path, *path_parts)

    return filepath


###############################################################################
##
##  Returns the maximum value in a specified column of 2D data
##

def get_max_of_column(data, column):
    
    # assume the max occurs in the first row
    max = data[0][column]
    for i in range(0, len(data)):
        if data[i][column] > max:
            max = data[i][column]
    
    return max


###############################################################################
##
##  Very ugly method to find out if a string is a number or not
##

def is_number(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


###############################################################################
##
## Takes an email address and extracts the username for d2l from it
##

def get_username_from_email(emailaddr):

    # Determine from the student's email address what their d2l username is
    username = emailaddr.lower().strip()
    atloc = username.find('@')

    if atloc != -1:
        username = username[:atloc]
        # If a student is a faculty member they will have a dot in their email, but not login
        username = username.replace('.', '')

    return username


##################################################################################
##
##  Returns all the videos contained within a specified playlist (video set).
##

def get_videos_in_playlist(playlist, video_data):

    return list(filter(lambda x: x['set'] == playlist, video_data))


################################################################################
##
##  Gets a list of all the distinct videos within the video data
##

def get_distinct_videos(video_data):

    videos = []
    video_names = []

    for video in video_data:
        if not video['name'] in video_names:
            video_names.append(video['name'])
            videos.append(video)

    return videos


###############################################################################
##
##  Removes the middle initial that is placed on the student's first name in
##    YuJa. Tries to account for students with multiple first names
##

def remove_mid_inital(name):

    names = name.split(' ')

    # Most students only have first name an a single initial for them just
    #  return the first name
    
    if len(names) == 1:
        return names[0]

    else:

        # Otherwise, check to see if the last value provided is one character
        #  and if it is, remove it. The last statements joins the list elements
        #  into a string

        mid_initial = names[-1]
        if len(mid_initial) == 1:
            return ' '.join(names[0:-1])


###############################################################################
##
##  Converts seconds to HH:MM:SS
##

def format_seconds(seconds):
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{hours}:{minutes}:{seconds}"

###############################################################################
##
##  Gets a list of the videos that need to have reports downloaded
##

def get_videos_to_process(video_data):

    # first reduce the possibilities to only distinct videos withiin the
    #   video list

    temp_videos = get_distinct_videos(video_data)
    videos = []

    for video in temp_videos:
        if video['download_results']:
            videos.append(video)

    return videos


################################################################################
##
##  Gets a list of all the distinct video names within the video data
##

def get_distinct_video_names(video_data):

    video_names = []

    for video in video_data:
        if not video['name'] in video_names:
            video_names.append(video['name'])

    return video_names
    

################################################################################
##
##  Gets a list of all of the current playlist names
##

def get_video_playlists(video_data):

    playlists = []

    for video in video_data:
        if not video['set'] in playlists:
            playlists.append(video['set'])
    
    return playlists

###############################################################################
##
##  Gets all the view results for a particular student from a list
##

def get_views_for_student(config, student, view_data):

    db_config = config['database']
    found_views = []
    for view in view_data:
        lname = view[db_config['lname_col']] 
        fname = remove_mid_inital(view[db_config['fname_col']])
        if (fname in student.fname) and (lname in student.lname):
            found_views.append(view)
    return found_views
        

################################################################################
##
##  Gets a list of all videos having a common name. This can happen if they are
##    contained in different playlists
##

def get_videos_by_name(name, video_data):

    return list(filter(lambda x: x['name'] == name, video_data))

###############################################################################
##
##  Get a single video by name, regardless of which playlists it might be
##    stored in.

def get_video_by_name(name, video_data):
    
    for video in video_data:
        if video['name'] == name:
            return video
    
###############################################################################
##
##  Look up a student record by their d2l username, returns the student class
##    if it is found and None if it is not found
##

def get_student_by_username(course, username):
    
    for student in course.students:
        if student.username == username:
            return student
    return None

################################################################################
##
##  Returns a list of the lengths of the videos in a group
##

def get_video_lengths(video_data):

    lengths = []

    for video in video_data:
        lengths.append(video['length'])

    return lengths


################################################################################
##
##  Returns a list of the direct links for each video in yuja
##

def get_video_links(video_data):

    links = []

    for video in video_data:
        links.append(video['direct_link'])

    return links


################################################################################
##
##  Determines if any items within a list are None
##    e.g. [2, None, None] returns True
##         [None, 5, None, None] returns True
##         [6, 6, None] returns False
##

def has_missing_values(value_list):
    
    for item in value_list:
        if item == None:
            return True
        
    return False


################################################################################
##
##  Determines if all values are the same within a list, ignores values set to
##    None
##

def all_values_equal(value_list):
    
    # Remove all items in the list that are equl to None
    rm_none = list(filter(lambda item: item is not None, value_list))
    
    # If no items exist in the list then technically they are all the same
    if len(rm_none) == 0:
        return True
    
    # Check to make sure all other elements are the same
    value = rm_none[0]
    for item in rm_none:
        if item != value:
            return False
    
    return True


def test_all_values_equal():
    print(all_values_equal([]))
    print(all_values_equal([1]))
    print(all_values_equal(['hello']))
    print(all_values_equal([17, 17]))
    print(all_values_equal([19, 21]))
    print(all_values_equal([12, 12, 12]))
    print(all_values_equal([13, 12, 11]))
    print(all_values_equal([12, 12, 61]))
    print(all_values_equal([16, 16, None]))
    print(all_values_equal([None, 17, 17]))
    print(all_values_equal([None, 21, None, 35, None, 21]))


################################################################################
##
##  Gets the one non-None value within a list
##

def get_set_value(value_list):
    
    for value in value_list:
        if value != None:
            return value
    
    return None

################################################################################
##
##  This is required when writing the gradebooks because D2L does not store
##  SID's with leading zeros.
##

def remove_leading_zeros(sid):
    while sid[0] == '0':
        sid = sid[1:]
    return sid





###############################################################################
## MAIN PROGRAM - for testing
###############################################################################

if __name__ == '__main__':
    test_all_values_equal()