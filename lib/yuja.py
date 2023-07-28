import os, datetime, time, csv, json, random
import util

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.firefox import GeckoDriverManager


###################################################
##
## Used to test this file to make sure all functions are working properly
##

def test():
   
    import video

    config = util.load_config('config.toml')
    print(config['browser'])
    
    error, msg, videodata = video.load_video_data(config)

    download_new_reports(config, videodata)
    

####################################################
## 
## Opens up a web driver for the specified browser in the config file using selenium,
##   and logs in to YuJa using the credentials specified
##
    
def start_web_session(config):

    if config['browser'].upper() == "CHROME":
        
        chrome_options = webdriver.ChromeOptions()
        prefs = {'download.default_directory': os.getcwd()}
        chrome_options.add_experimental_option('prefs', prefs)
        chrome = Service(ChromeDriverManager().install())
        if config.get('headless', False) == True:
            chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(service=chrome, options=chrome_options)
        
    elif config['browser'].upper() == "FIREFOX":
        
        firefox = Service(GeckoDriverManager().install())
        options = FirefoxOptions()
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.dir", os.getcwd())
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "document/csv;text/csv")
        if config.get('headless', False) == True:
            options.add_argument("--headless")
        driver = webdriver.Firefox(service=firefox, options=options)

    # Log into the website
    driver.get("https://tridenttech.yuja.com/Login?accesstype=YuJa%20Credentials")
    random_wait(10, 15)

    elem = driver.find_element(By.ID, "loginuserid")  
    elem.send_keys(config['username'])
    random_wait(2, 6)

    elem = driver.find_element(By.ID, "password")
    elem.send_keys(config['password'])
    random_wait(2, 6)

    elem = driver.find_element(By.ID, "loginButton").click()
    random_wait(10, 15)

    return driver


#######################################################
##
## Downloads view data from the YuJa website for the videos specified in the
##   videodata file and saves them to the reports folder.
##

def download_new_reports(config, videodata):
    
    error = 0
    msg = ''

    ## Reduce video data down to a distinct list so that duplicate video data
    ## Is not accidentally downloaded multiple times
    ##
    download_links = util.get_videos_to_process(videodata)

    if config['download_reports'] and len(download_links) > 0:
    
        driver = start_web_session(config)

        count = 1
        total = len(download_links)
        
        for video in download_links:

            results = []
            timestart = datetime.datetime.now()
            
            msg += f'Downloading report: {video["name"]} from YuJa ({str(count)} of {str(total)})\n'
            print(f'Downloading report: {video["name"]} from YuJa ({str(count)} of {str(total)})\n')

            # open the website the contains the individual student view data 
            #   and pull that information for the current course
            data_link = "view-source: https://tridenttech.yuja.com/Dashboard/Analytics/Data/UserVideoPlaybackStatisticsJSON"
            data_link += f"?videoPID={video['yuja_id']}&classPID=-1&userPID=0&getUserInfoFlag=0"
            driver.get(data_link)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            data = soup.body.text;
            views = json.loads(data)

            timeend = datetime.datetime.now()
            msg += f"Time to download: {(timeend - timestart).total_seconds()} seconds.\n"
            print(f"Time to download: {(timeend - timestart).total_seconds()} seconds.\n")

            random_wait(2, 4);
            # Next get the data that contains the total view length for each
            #   student regardless of how many views are posted
            data_link = "view-source: https://tridenttech.yuja.com/Dashboard/Analytics/Data/UserVideoTotalPlayLengthJSON"
            data_link += f"?videoPID={video['yuja_id']}&classPID=-1&userPIDs[]=-1"
            driver.get(data_link)
            
            soup = BeautifulSoup(driver.page_source, "html.parser")
            data = soup.body.text;
            view_lengths = json.loads(data)['data']['totalPlayLengths']

            # grab the usefult data from that object, note that times are
            #   given in milliseconds which is why the division by 1000
            for view in views['data']:

                # If a view length isn't specified, then default to zero
                if view['totalPlayLength'] == None:
                    view['totalPlayLength'] = 0
                    
                # Find the total view length for all views from this student
                pid = view['userPID']
                combinedPlayTime = 0
                
                for length in view_lengths:
                    if length['userPID'] == pid:
                        combinedPlayTime = length['totalPlayLength']
                        break
                    
                record = {
                    'lastname': view['lastname'],
                    'firstname': view['firstname'],
                    'videoname': video['name'],
                    'videolength': video['length'],
                    'playlength': round(view['totalPlayLength'] / 1000),
                    'totalplaytime': round(combinedPlayTime / 1000),
                    'starttime': datetime.datetime.fromtimestamp(view['firstWatched'] / 1000),
                    'endtime': datetime.datetime.fromtimestamp(view['lastWatched'] / 1000)
                }
                results.append(record)

            # write the view data to a file on disk to save for futher processing
            report_path = os.path.join(config['report_folder'], f"{video['name']}_report.csv")
            with open(report_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['lastname', 'firstname', 'videoname', 'videolength', 'playlength', 'totalplaytime', 'starttime', 'endtime'])
                for record in results:
                    row = []
                    row.append(record['lastname'])
                    row.append(record['firstname'])
                    row.append(record['videoname'])
                    row.append(record['videolength'])
                    row.append(record['playlength'])
                    row.append(record['totalplaytime'])
                    row.append(record['starttime'])
                    row.append(record['endtime'])
                    writer.writerow(row)

            # wait before loading the data from the next file
            random_wait(5, 10);
            count += 1

        end_web_session(driver)

    return error, msg


####################################################
## Erases the usage data saved on Yuja's website, this is needed when the
##   number of views for a video gets to be very high and it starts taking
##   longer to download the view results. For classes like MAT 120 and MAT 110
##   this should happen minimally at the end of each semster, but possibly even
##   at the end of each term. It is not advised to perform this during a term
##   to prevent the loss of current view data.

## TODO:

def delete_view_data_on_yuja(config, videodata):
    
    error = 0
    msg = ''

    ## Reduce video data down to a distinct list so that duplicate video data
    ## Is not accidentally downloaded multiple times
    ##
    videos_to_process = util.get_videos_to_process(videodata)
    
    print(f'\n\nWARNING: You have set the flag "clear_online_data" in the file' \
         + ' config.toml. This will delete all the results stored online for' \
         + ' the videos in the database "video_data.csv" that have a DOWNLOAD_RESULTS' \
         + ' flag set to TRUE. It will not delete any previously saved data from the' \
         + ' the main database store or have any effect on previously generated' \
         + ' gradebooks.\n')
    
    intent = input('Is this what you intend to do? (Y/n): ')

    if (intent == 'Y') and config['clear_online_data'] and (len(videos_to_process) > 0):
    
        driver = start_web_session(config)

        count = 1
        total = len(videos_to_process)
        
        for video in videos_to_process:
            
            msg += f'Deleting Online Results for: {video["name"]} from YuJa ({str(count)} of {str(total)})\n'
            print(f'Deleting Online Results for: {video["name"]} from YuJa ({str(count)} of {str(total)})\n')

            # submit a POST request to the website responsible for removing the video results
            js = f"var xhr = new XMLHttpRequest();\n" \
            f"xhr.open('POST', 'https://tridenttech.yuja.com/Dashboard/TMSIKUGCCT/Data/ClassVideoPlaybackStatisticsJSON', false);\n" \
            f"xhr.setRequestHeader('Content-type', 'application/x-www-form-urlencoded; charset=UTF-8');\n" \
            f"xhr.setRequestHeader('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/111.0');\n" \
            f"xhr.send('videoPID={video['yuja_id']}');\n" \
            f"return xhr.response;\n"

            result = driver.execute_script(js)
            resultObj = json.loads(result)
            success = resultObj.get("success")
            if success:
                msg += f'Response from server: Success'
                print('Response from server: Success')
            else:
                msg += f'Response from server: Error ... aborting!'
                print('Response from server: Error ...aborting!')
                error = -1
                break

            random_wait(5, 10)

        end_web_session(driver)

    return error, msg
    


####################################################
##
## Closes a selenium browsing session
##

def end_web_session(driver):
    driver.close()
    driver.quit()


####################################################
##
## Calls up a website on yuja that contains the length of a video and returns that value
##  as an integer in seconds
##

def get_video_length(driver, id):

    data_link = "view-source:https://tridenttech.yuja.com/P/Data/VideoListJSON?includeAllClasses=false"
    data_link += f"&videoID%5B%5D={id}"
    driver.get(data_link)
    random_wait(8, 15)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    data = soup.body.text;

    video_data = json.loads(data)
    length = int(video_data["data"][0]["duration"])

    return length


####################################################
##
## To slow down the rate of requests made on YuJa's servers, this function pauses
##   execution of the script for a random amount of time
##

def random_wait(a, b):
    wait = a + (b-a) * random.random()
    print(f'Waiting: {wait} seconds.')
    time.sleep(wait)

##################################################
##                                    Main Program
##################################################

if __name__ == "__main__":
    test()
