"""
Given a map thread, parses comments to get urls, downloads png and json data,
posts data as request to some_bot_server to upload map data
"""

import re
import json

import requests
import praw


map_thread = "http://www.reddit.com/r/TagPro/comments/20usrv/monthly_map_rotation_thread_26/"


def get_json_png_urls(comments, links=None):
    if not links:
        links = []
    for index, comment in enumerate(comments):
        try:
            comment_links = re.findall(
                r'href="(.*?(imgur|pastebin|lpaste).*?)"', comment.body_html)
            if comment_links:
                links.append(comment_links)
            else:
                print "Couldn't find links in comment: ", comment
        except:  # TODO: This is really broad.
            if type(comment) == 'praw.objects.MoreComments':
                get_json_png_urls(comment.comments(), links)
    return links


def extract_links(links):
    """ links is a list of links from each comment. Instead of trying to parse
    the comment, grab the links in the comment, download the pastebin and grab
    the imgur link. We test the size, if it's smaller than a set amount (15 kB),
    it's likely to be a png file so use it"""

    json_data = None
    png_data = None
    for link in links:
        url, host = link
        if host == "pastebin":
            paste_id = url.split("/")[-1].split("=")[-1]
            json_url = "http://pastebin.com/raw.php?i=" + paste_id
            json_data = requests.get(json_url).text
        elif host == "lpaste":
            paste_id = url.split("/")[-1]
            json_url = "http://lpaste.net/raw/" + paste_id
            json_data = requests.get(json_url).text
        elif host == "imgur":
            # Need to get png file and not preview file
            if url[-4:].lower() != ".png":
                url += ".png"
            r = requests.get(url)
            size = int(r.headers['content-length'])
            # Filter by image size to determine if png or preview
            if size < 15000:
                png_data = r.content
    return json_data, png_data


def main():
    total = 0
    failed = 0
    failed_links = []

    reddit = praw.Reddit("TagPro Mapthread Parser")
    comment_links = get_json_png_urls(
        reddit.get_submission(map_thread, comment_limit=200).comments)

    for links in comment_links:
        # This is the 'map' level
        json_data, png_data = extract_links(links)

        if png_data and json_data:
            json_info = json.loads(json_data)['info']
            mapname = json_info['name']
            author = json_info.get('author', "No author listed")
            print "Posting {}....".format(mapname)
            files = {"logic": json_data, "layout": png_data}
            r = requests.post("http://localhost:5000/",
                              data={"mapname": mapname, "author": author},
                              files=files)
            print "Status: ", r.status_code
            total += 1
        else:
            failed_links.append(links)
            failed += 1

    print "Successfully wrote %s files... %s failed" % (total, failed)
    print u"Couldn't load the following urls:\n{0:s}\n".format(
        "\n".join("\t" + x[0] for x in failed_links))

if __name__ == "__main__":
    main()