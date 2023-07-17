## NOTES
#
# Video Set - The name of the course the video corresponds with. This should
#   match up with an instructor's name in the class/instructor database.
# Video Name - the name of the video as it is stored on YuJa
# D2L Name - the name of the video in the D2L gradebook
# Length - the length of the video in milliseconds (will populate on its own)
# download_results - whether to download the results for this video or not
# direct_link - the direct link for the video found on yuja

import csv
import os

import util
import yuja

# video_object:
#
#   set - string: mat120
#   name - string: mat120_1-1_video
#   d2lname - String, looks like: 1.1 Video Points Grade
#   length - Integer - the length of the video in milliseconds
#   download_results - boolean
#   yuja_id - string: identifier for the video on yuja


#################################################
##
##  Just for testing purposes to make sure this module is working
##    properly
##

def test():

    from pprint import pprint
   
    config = util.load_config('../config.toml')

    error, msg, video_data = load_video_data(config)

    playlists = util.get_video_playlists(video_data)

    for playlist in playlists:

        videos = util.get_videos_in_playlist(playlist, video_data)

        length = 0
        for video in videos:
            if video['length'] != None:
                length += video['length']
        
        print(f"Playlist: {playlist}  length: {util.format_seconds(length)}")
    

#################################################
##
## Loads the video data from the video data file and retrieves the
##   length of any videos from YuJa for any video where the length
##   is not specified.
##

def load_video_data(config):

    error = 0
    return_msg = ""
    video_data = []
    webdriver = None
    update_video_file = False
    
    video_config = config['video_data']
    video_data_filename = video_config['filename']

    # Gather the requisite data about the videos
    if os.path.exists(video_data_filename):
        video_data_file = open(video_data_filename)
        video_list = list(csv.reader(video_data_file))
        # Delete the first row of data which is just column titles
        video_list = video_list[1:]
        
    else:
        error = -1
        msg = f"\n[ ERROR ] Video database file {video_data_filename} not found. " \
              "This should be located in the same directory where the script is located.\n"
        return_msg += msg
        if not config['suppress_console_output']:
            print(msg)
        return error, return_msg, video_data

    try:
        
        for line in video_list:

            # Retrieve the video set that the video belongs in
            videoset = line[video_config['videoset_col']]
            
            # Retrieve the name of the video
            videoname = line[video_config['videoname_col']]

            # Retrieve the name of the video within the D2L gradebook
            d2lname = line[video_config['d2lname_col']]

            # Check to see if the video results should be downloaded (convert to boolean)
            download_results = line[video_config['downloadresults_col']].lower() in ['true', 't', '1', 'yes', 'y']

            # Preserve the direct link for re-writing the videodata file
            direct_link = line[video_config['directlink_col']]

            # Use the direct link provided to obtain the yuja video id
            video_id_found = False
            yuja_id = None
            
            # First grab the individual html parameters from the direct link
            if "?" in direct_link:
                parameters = direct_link.split("?")[1].split("&")
                for param in parameters:
                    key, value = param.split("=")
                    if (key == "v") and (not video_id_found):
                        yuja_id = value
                        video_id_found = True
            else:
                # indicate that a direct link was not found
                direct_link = None
                    
            if not video_id_found:
                error = 1
                msg = f"\n[ WARNING ] Direct link for video {videoname} does not contain a " \
                      "video ID number. Check the direct_link in 'videodata.csv' to make " \
                      "sure it has an item like: v=5010426.\n"
                return_msg += msg
                if not config['suppress_console_output']:
                    print(msg)

            # Get the length of the video, unless we aren't going to download results anyway
            if (line[video_config['length_col']] == '') and download_results:
                
                # Any unspecified lengths for video files should be obtained by contacting yuja
                if webdriver == None:
                    webdriver = yuja.start_web_session(config)

                length = yuja.get_video_length(webdriver, yuja_id)
                update_video_file = True

                msg = f"\n[ NOTICE ] Video length for {videoname} was not specified. " \
                       f"Acquiring data from Yuja.\n"
                return_msg += msg
                if not config['suppress_console_output']:
                    print(msg)

            elif util.is_number(line[video_config['length_col']]):
                length = round(float(line[video_config['length_col']]))
            else:
                length = None

            video = { 
                'set' : videoset, 
                'name' : videoname,
                'd2lname' : d2lname,
                'length' : length,
                'download_results' : download_results,
                'direct_link' : direct_link,
                'yuja_id' : yuja_id 
            } 

            video_data.append(video)

            
    except IndexError:
        error = 1
        msg = f"\n[ ERROR ] Format error likely in the video database file, " \
               f"{video_data_filename} at video {video['name']}\n"
        return_msg += msg
        if not config['suppress_console_output']:
            print(msg)

    if webdriver != None:
        yuja.end_web_session(webdriver)

    # If new data was acquired, write the new video data to the ouput file
    if update_video_file:
        export_video_data(config, video_data)

    return error, return_msg, video_data


#################################################
##
## Writes the video data contained in memory to disk. This only
##   happens when the script has to pull new data for the length
##   of a video from YuJa and is called automatically. There is
##   no need to call this function directly
##

def export_video_data(config, videodata):

    video_config = config['video_data']
    video_data_filename = video_config['filename']

    with open(video_data_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['videoset', 'video_name', 'd2l_name', 'length', 'download_results', 'direct_link'])
        for video in videodata:
            row = []
            row.append(video['set'])
            row.append(video['name'])
            row.append(video['d2lname'])
            row.append(video['length'])
            row.append(video['download_results'])
            row.append(video['direct_link'])
            writer.writerow(row)


################################################################################
##
##  Goes through the video data and tries to fill in any missing data, also
##    alerts to any mistakes in the data
##

def verify_video_data(config, video_data):

    error = 0
    msg = ""
    data_updated = False

    new_video_data = []
    distinct_video_names = util.get_distinct_video_names(video_data)

    for video_name in distinct_video_names:

        # pick up each group of videos that have a similar name
        videos = util.get_videos_by_name(video_name, video_data)
        
        # if only one video exists by that name, we don't need to check anything
        if len(videos) == 1:
            new_video_data.extend(videos)
        
        else:
            # Get the lengths of each video in the group
            lengths = util.get_video_lengths(videos)

            # if the length of some of those videos are set, then update the
            #   other videos to that length
            if util.has_missing_values(lengths) and util.all_values_equal(lengths):
                value = util.get_set_value(lengths)
                for video in videos:
                    video['length'] = value
                    new_video_data.extend([video])
                    data_updated = True

            # otherwise if they are not all equal lengths, flag an error
            elif not util.all_values_equal(lengths):
                error = -1
                msg = f"\n[ ERROR ] Video {video_name} has different lengths reported in " \
                      f"more than one location of videodata.csv.\n"
                return error, msg, video_data

            # Now do the same for the direct links
            links = util.get_video_links(videos)

            if util.has_missing_values(links) and util.all_values_equal(lengths):
                value = util.get_set_value(links)
                for video in videos:
                    video['direct_link'] = value
                    new_video_data.extend([video])
                    data_updated = True

            # otherwise if they are not all equal lengths, flag an error
            elif not util.all_values_equal(links):
                error = -1
                msg = f"\n[ ERROR ] Video {video_name} has different direct links " \
                      f"reported in more than one location of videodata.csv.\n"
                return error, msg, video_data
            
            new_video_data.extend(videos)
            
    if data_updated:
        export_video_data(config, video_data)

    return error, msg, new_video_data

##################################################
##                                    Main Program
##################################################

if __name__ == "__main__":
    test()
