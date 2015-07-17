#Creates a new daily post.
import praw
import time
import configparser
import sys
from OAuth2PrawLogin import redditlogin
from ScoreBotTypes import SteamUserScore, SteamScorePost
import pickle
from datetime import date, timedelta

config = configparser.ConfigParser()
config.read(sys.argv[1])

today = date.today()

#Yesterday's postID used to unsticky posts.
yesterdayID = 0

#Login
r = praw.Reddit('Steam Score Leaderboard Maintainer by u/Avagad')
redditlogin(r, config['User']['clientid'], config['User']['secretkey'], config['User']['username'], config['User']['password'])
#If this throws an exception (e.g. timout) there's no real point carrying on. Just wait for the script to be called again.

#Get saved posts
try:
    with open(config['Subreddit']['postdata'], "rb") as f:
        postdata = pickle.load(f)
except:
    postdata = set()

poststodelete = set()
#First clean up old complilation posts
for comppost in (scoreposts for scoreposts in postdata if scoreposts.type==2):
    if abs(comppost.date - today) > timedelta(days = int(config['Subreddit']['compdaysavailable'])):
        submission = r.get_submission(submission_id=comppost.postid)
        #submission.delete()
        poststodelete.add(comppost)

#Then clean up old dailes                
for dailypost in (scoreposts for scoreposts in postdata if scoreposts.type==0):
    if abs(dailypost.date - today) > timedelta(days = int(config['Subreddit']['dailydaysavailable'])):
        submission = r.get_submission(submission_id=dailypost.postid)
        submission.delete()
        poststodelete.add(dailypost)

    #Get Yesterday's ID in case we need to unsticky later
    if dailypost.date == (today - timedelta(days = 1)):
        yesterdayID = dailypost.postid

for dailypost in (scoreposts for scoreposts in postdata if scoreposts.type==1):
    if abs(dailypost.date - today) > timedelta(days = int(config['Subreddit']['dailydaysavailable'])):
        poststodelete.add(dailypost)


#Then check if any posts have been deleted through reddit
for post in postdata:
    submission = r.get_submission(submission_id=post.postid)
    if not submission.author:
        poststodelete.add(post)

#Update the postdata set
for post in poststodelete: postdata.discard(post)

#Check whether a post has already been made today
exists = False
for post in postdata:
    if post.date == today and post.type == 0:
        exists = True

#Create new daily post and catch any timeout exceptions
if not exists:
    for attempt in range(30):
        try:
            submission = r.submit(config['Subreddit']['name'], config['Daily Post']['title'] + " - " + today.strftime(config['Daily Post']['dateformat']), text = str(config['Daily Post']['bodytext']).replace("\\n","\n"),  send_replies=False)
        except Exception as inst:
            print(type(inst))     #Default catch. Print it to track in the future.
            time.sleep(60)
            continue
        if config.getboolean('Subreddit','stickydaily'):
            if yesterdayID != 0:
                yestPost = r.get_submission(submission_id=yesterdayID)
                yestPost.unsticky()
            try:
                submission.sticky()
            except praw.errors.ModeratorOrScopeRequired:
                pass #Not a moderator. TODO: Check for moderator status.
        #Add post to postdata
        postdata.add(SteamScorePost(submission.id, today, 0))
        break

#Check whether a post has already been made today
exists = False
for post in postdata:
    if post.date == today and post.type == 2:
        exists = True
#Create new weekly post and catch any timeout exceptions
#TODO: Update to make more generic. Monthly, Fortnightly etc.
if today.weekday() == 0 and not exists:
    for attempt in range(30):
        try:
            submission = r.submit(config['Subreddit']['name'], config['Weekly Post']['title'] + " - " + today.strftime(config['Weekly Post']['dateformat']), text = str(config['Weekly Post']['bodytext']).replace("\\n","\n"),  send_replies=False)
        except Exception as inst:
            print(type(inst))     #Default catch. Print it to track in the future.
            time.sleep(60)
            continue
        if config.getboolean('Subreddit','stickycomp'):
            try:
                submission.sticky()
            except praw.errors.ModeratorOrScopeRequired:
                pass #Not a moderator. TODO: Check for moderator status.
        #Add post to postdata
        postdata.add(SteamScorePost(submission.id, today, 2))
        break

for post in postdata:
    print(post.date ,post.postid ,post.type )

#Save our updated post data
with open(config['Subreddit']['postdata'], 'wb') as f:
    pickle.dump(postdata, f, pickle.HIGHEST_PROTOCOL)
