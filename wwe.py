#!/usr/bin/python3

import arrow
import requests
import CONSTANTS


class wwe_network:

    def __init__(self, user, password):

        with requests.Session() as self._session:
            self._session.headers.update(CONSTANTS.HEADERS)

        self.user = user
        self.password = password
        self.logged_in = False

    def refresh_token(self):
        if not self.refreshToken:
            print("No refresh token found")
            return
        xx = self._session.post('https://dce-frontoffice.imggaming.com/api/v2/token/refresh', json={'refreshToken': self.refreshToken})
        exit()


    def _set_authentication(self):

        access_token = self.authorisationToken
        if not access_token:
            print("No access token found.")
            return

        self._session.headers.update({'Authorization': f'Bearer {access_token}'})
        print("Succesfully logged in")
        self.logged_in = True

    def login(self):

        payload = {
            "id": self.user,
            "secret": self.password
        }

        token_data = self._session.post('https://dce-frontoffice.imggaming.com/api/v2/login', json=payload, headers=CONSTANTS.REALM_HEADERS).json()
        if 'code' in token_data:
            print("Error while logging in. Possibly invalid username/password")
            exit()


        self.authorisationToken = token_data['authorisationToken']
        self.refreshToken = token_data['refreshToken']

        self._set_authentication()

    # Get the m3u8 stream
    def m3u8_stream(self, stream_link):

        #https://dve-api.imggaming.com/v/70800?customerId=16&auth=1f7512c7c2b7474abf723188038b32c1&timestamp=1564126721496
        stream = self._session.get(stream_link, headers=CONSTANTS.REALM_HEADERS).json()

        # Get our subtitle stream
        subtitle_stream = ''
        for i in stream['subtitles']:
            if i['format'] == "vtt":
                subtitle_stream = i['url']
                break
            
        return stream['hls']['url'], subtitle_stream


    # Download the subtitles to the temp folder
    def download_subtitles(self, link, episode_title):
        # Get the substitle file
        subtitle_data = self._session.get(link).content.decode()
        print("\nStarting to write the subtitle file")

        # Open and write the subtitle data
        vtt_file = open(f"{CONSTANTS.TEMP_FOLDER}/{episode_title}.vtt", "w")
        vtt_file.write(subtitle_data)
        
        print("Finished writing the subtitle file")
        # Close the file
        vtt_file.close()



    def get_chapter_information(self, link, episode_title, chapterize=False):
        api_link = self._session.get(f'https://cdn.watch.wwe.com/api/page?path={link}').json()

        entry = api_link["entries"][0]["item"].get("relatedItems")
        data = []
        for i in entry:
            if i.get("relationshipType") == "milestone":
                start = int(i["item"]["customFields"].get("StartPoint") * 1000)
                end   = int(i["item"]["customFields"].get("EndPoint") * 1000)

                title = i["item"].get("title")
                data.append([start, end, title])

        print("\nStarting to write the metadata file")
        meta_file = open(f"{CONSTANTS.TEMP_FOLDER}/{episode_title}-metafile", "w")
        meta_file.write(f";FFMETADATA1\n\
title={episode_title}\n")
        print("Finished writing the metadata file")

        if chapterize:
            print("\nWriting chapter information")
            for i in data:
                meta_file.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={str(i[0])}\nEND={str(i[1])}\ntitle={i[2]}\n\n")

            print("Finished writing chapter information")

        print("\nStarting to write the stream title")
        meta_file.write(f"[STREAM]\ntitle={episode_title}")
        print("Finished writing the stream title\n")
        meta_file.close()

    def _video_url(self, link):
        #playerUrlCallback=https://dve-api.imggaming.com/v/70800?customerId=16&auth=33d8c27ac15ff76b0af3f2fbfc77ba05&timestamp=1564125745670
        video_url = self._session.get(f'https://dce-frontoffice.imggaming.com/api/v2/stream/vod/{link}', headers=CONSTANTS.REALM_HEADERS).json()
        try:
            if video_url['status'] == 403:
                print("Your subscription is invalid. Quitting.")
                exit()
        except:
            return video_url['playerUrlCallback'], video_url['videoId']

    def get_video_info(self, link):
        # Link: https://cdn.watch.wwe.com/api/page?path=/episode/This-Tuesday-in-Texas-1991-11831
        # We need   DiceVideoId
        api_link = self._session.get(f'https://cdn.watch.wwe.com/api/page?path={link}').json()

        # If we have an invalid link, quit
        try:
            if api_link["message"]:
                print("Video link is invalid. Exiting now..")
                return
        except:
            pass

        entry = api_link['entries'][0]['item']

        # If our event is a weekly/episodic show, add the date, season and episode number to the file name
        if entry["customFields"].get("EventStyle") == "Episodic":
            if entry["episodeNumber"] < 10:
                ep_num = "0" + str(entry["episodeNumber"])
            else:
                ep_num = entry["episodeNumber"]

            file_date = arrow.get(
                    entry["firstBroadcastDate"], "YYYY-MM-DDTHH:mm:ssZ"
            )
            file_date = file_date.format("MM-DD-YYYY")

            file_name = "{} {} - S{}E{} - {}".format(
                entry["customFields"]["Franchise"],
                entry["episodeName"]
                .replace("&", "and")
                .replace(":", "- ")
                .replace("'", "")
                .replace("\"", "")
                .replace("/", " "),
                entry["releaseYear"],
                ep_num,
                file_date,
            )
        elif entry["customFields"].get("SeasonNumber") and entry["customFields"].get("EventStyle") != "PPV":
            if entry["episodeNumber"] < 10:
                ep_num = "0" + str(entry["episodeNumber"])
            else:
                ep_num = entry["episodeNumber"]

            file_date = arrow.get(
                    entry["firstBroadcastDate"], "YYYY-MM-DDTHH:mm:ssZ"
            )
            file_date = file_date.format("MM-DD-YYYY")

            file_name = "{} - S{}E{} - {}".format(
                entry["customFields"]["SeriesName"],
                entry["customFields"].get("SeasonNumber"),
                ep_num,
                entry["episodeName"]
                .replace("&", "and")
                .replace(":", "- ")
                .replace("'", "")
                .replace("\"", "")
                .replace("/", " "),
            )

        elif entry["customFields"].get("EventStyle") == "PPV":
            # If it is a PPV get the title and year into variables
            ppv_title = entry["episodeName"]
            ppv_year = entry["releaseYear"]
            # Check if the PPV already has the year in it. For example "This Tuesday in Texas 1991" has the year,
            # but "WrestleMania 35" doesn't. Since we don't want to have "This Tuesday in Texas 1991 1991" as
            # our filename we will just use the PPV title
            if str(ppv_year) in ppv_title:
                file_name = f'{entry["customFields"]["Franchise"]}k {entry["episodeName"]}'
            else:
                file_name = f'{entry["customFields"]["Franchise"]} {entry["episodeName"]} {entry["releaseYear"]}'
        else:
            if not entry.get('title'):
                raise Exception("Unrecognized event type")
            file_name = (
                entry["title"]
                .replace("&", "and")
                .replace(":", "- ")
                .replace("'", "")
                .replace("\"", "")
                .replace("/", " ")
            )

        video_url_resp = self._video_url(api_link['entries'][0]['item']['customFields']['DiceVideoId'])
        return video_url_resp[0], file_name, video_url_resp[1]


if __name__ == "__main__":
    print("Please run python main.py instead.")
    pass
