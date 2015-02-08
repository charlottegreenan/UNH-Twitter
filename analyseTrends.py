#!/usr/bin/python -tt

""" Analyse adoptions of keyword """

import pickle
import re
import numpy as np
import sys
import subprocess
import MySQLdb as mdb
import os


## find tweets with keyword mentioned as string
def tweetsWithKeywordAsString(keyword):
	con = mdb.connect('localhost', 'testuser2', 'test623', 'TWITTER');
	cur = con.cursor()
	cur.execute("SELECT text, actors.id, tweets.id, screen_name FROM tweets JOIN actors on tweets.author_ID=actors.author_ID where lower(text) like '%"+keyword+"%'")
	tweets = cur.fetchall()
	con.close()
	return tweets

## find tweets with keyword mentioned as word
def tweetsWithKeywordAsWord(tweets, keyword):
	tweets2 = []
	for tweet in tweets:
		newwords = re.findall("[\w\d]+",tweet[0].decode('utf-8').lower())
		if keyword in newwords:
			tweets2 += [tweet]
	return tweets2

## find new tweeters mentioning keyword
## i.e. just first instance for each actor
def newTweeters(tweets, keyword):
	tweeted = []
	tweets2 = []
	for tweet in tweets:
		if tweet[1] not in tweeted:
			tweets2 += [tweet]
			tweeted += [tweet[1]]
	return [tweet[1:] for tweet in tweets2]

def saveTweetTimes(adopters):
	tweeters = ""

	for adopter in adopters:
		tweeters += str(adopter[0])+","
		tweeters += str(adopter[1])+"\n"
	
	file = open("csvFiles/adoptions.csv", "w")
	file.write(tweeters)
	file.close()

## run R script
def callRfunctions(keyword):
	myCommand = "mkdir pics/"+ keyword
	subprocess.call(myCommand, shell=True)
	subprocess.call("Rscript Rscripts/contagion.r", shell=True)

def makeGIF(keyword, n):
	gifExists = os.path.isfile("pics/"+keyword+"/animation"+keyword+".gif")
	print
	if gifExists:
		print "GIF exists already!"
	else:
		print "Making GIF..."
		myCommand = "convert -delay 20 pics/"+keyword+"/influenceNetwork"+keyword
		myCommand += "*.png pics/"+keyword+"/animation"+keyword+".gif"
		subprocess.call(myCommand, shell=True)
	subprocess.call("rm pics/"+keyword+"/influenceNetwork*.png", shell=True)

def makeHTML(keyword,tweetsAll):
	htmlStr = """
	
	<!DOCTYPE html>
	<html>
	<head>
	<link rel="stylesheet" type="text/css" href="charlottestyle.css">
	<meta content="text/html; charset=utf-8" http-equiv="Content-Type" />
	<title>%s</title>
	<meta content="width=device-width, initial-scale=1.0" name="viewport" />
	</head>
	<body>
	<h1><i>%s</i></h1>
	<div class="container" style="margin-top:20px;min-height:1150px;">
	
		<div style="width:1150px;float:left;min-height:450px;">
			<hr>
			<h3> Analysis</h3>
			<hr>
			<div style="width:300px;float:left;min-height:100px;margin-right:10px;">
				<div class="myleft2">
				<figcaption><h4>Total number of people tweeting about '%s'</h4> </figcaption>
				<img src="../pics/%s/plot1.png" style="width:250px;height:250px">
				</div>
			</div>
			
			<div style="width:300px;float:left;min-height:100px;margin-right:20px;">
				<div class="myleft3">
				<figcaption><h4>Growth in number of people tweeting about '%s'</h4> </figcaption>
				<img src="../pics/%s/plot2.png" style="width:250px;height:250px">
				</div>
			</div>
		
	"""%(keyword.lower(),keyword.lower(),keyword.lower(),keyword,keyword.lower(),keyword)

	
	htmlStr += """
		<div style="width:500px;float:left;min-height:100px;">
	<h3>Cox regression model<h5>(model chosen by AIC)</h5></h3>
	<table id="mytable" style="width:500px;">
	<tr>
	<td><b>Effect</b> </td>
	<td><b>Parameter</b></td>
	<td><b>Std. error</b></td>
	<td><b>P values</b></td>
	</tr>
	"""

	file = open("csvFiles/finalModel.csv", "r")
	finalModel = file.readlines()
	file.close()

	for row in finalModel:
		htmlStr += """<tr>"""
		entries = row.split('","')
		entries[0] = entries[0][1:]
		entries[4] = entries[4][:-2]
		htmlStr += """<td>"""+str(entries[0])+"""</td>"""
		htmlStr += """<td>"""+str(entries[1])+str(entries[2])+"""</td>"""
		for entry in entries[3:]:
			htmlStr += """<td>"""+str(entry)+"""</td>"""
		htmlStr += """</tr>"""

	htmlStr += """</table></div></div>"""

### Potential influence plot

	htmlStr += """
	<div style="width:1150px;float:left;min-height:600px;">
		<hr>
		<h3> Visualising potential influence</h3>
		<hr>
		<div style="width:550px;float:left;min-height:600px;">
			<ul>
			<li><h4>Earliest adopters are red; latest adopters are blue.</h4></li>
			<li><h4>Node size indicates estimated potential influence.</h4></li>
			<li><h4>Squares indicate the most influential nodes.</h4></li>
			<li><h4>Edges show paths of potential influence.</h4></li>
			</ul>
		</div>
		<div style="width:600px;float:left;">
			<div class="myleft">
			<img src="../pics/%s/animation%s.gif" style="width:550px;height:550px">
			</div class="myleft">
		</div>
	</div>
	"""%(keyword,keyword.lower())
	
## Top tweeters table

	file = open("csvFiles/topTweeters.csv", "r")
	topTweeters = file.readlines()
	file.close()
	
	if topTweeters:
		htmlStr += """
			<div style="width:1150px;float:left;min-height:50px;">
			<hr>
			<h3> Influential tweeters</h3>
			<hr>
			</div>
		"""

		influential = [int(re.findall('[\d]+',t)[0]) for t in topTweeters]
		infMult = [re.findall(',([\d.]+)',t)[0] for t in topTweeters]

		firstTweet = {}
		screenNames = {}
		for actor in influential:
			firstTweet[actor] = ""
			screenNames[actor] = ""

		for tweet in tweetsAll:
			if tweet[1] in influential and keyword in tweet[0].lower():
				if not firstTweet[tweet[1]]:
					firstTweet[tweet[1]] = tweet[0]
					screenNames[tweet[1]] = tweet[3]

		file = open("csvFiles/topTweetersIndegree.csv", "r")
		indeg = [f[:-1] for f in file.readlines()]
		file.close()
	
		file = open("csvFiles/topTweetersNoPotentInfl.csv", "r")
		potInf = [f[:-1] for f in file.readlines()]
		file.close()

		htmlStr += """

		<table id="mytable" style="width:1150px;">
		<tr>
		<td><b>Tweeter</b> </td>
		<td><b>Percentage increase in followers' rate of adoption</b></td>
		<td><b>No. of followers</b> </td>
		<td><b>No. potentially influenced</b> </td>
		<td><b>First tweet about %s</b></td>
		</tr>
		"""%keyword.lower()

		for i in range(len(influential)):
			htmlStr +=  """<tr>"""
			htmlStr += """<td>"""+screenNames[influential[i]]+"""</td>"""
			htmlStr += """<td>"""+str(infMult[i])+"""</td>"""
			htmlStr += """<td>"""+str(indeg[i])+"""</td>"""
			htmlStr += """<td>"""+str(potInf[i])+"""</td><td>"""
			htmlStr += firstTweet[influential[i]]
			htmlStr += """</td></tr>"""

		htmlStr += """</table>"""
	else:
		htmlStr += """<div></div> """
	htmlStr += """</div>
	</body>
	</html>
	"""
	return htmlStr
	
def saveAndLaunchHTML(htmlStr, keyword):
	fileName = "html/results"+keyword+".html"
	file = open(fileName, "w")
	file.write(htmlStr)
	file.close()
	commandName = "open -a Google\ Chrome html/results"+keyword+".html"
	subprocess.call(commandName, shell=True)

def main():
	keyword = sys.argv[1]
	
	## save keyword for use in R
	file = open("csvFiles/keyword.csv", "w")
	file.write(keyword+"\n")
	file.close()
	
	tweets = tweetsWithKeywordAsString(keyword)
	tweets = tweetsWithKeywordAsWord(tweets, keyword)
	adopters = newTweeters(tweets,keyword)
	saveTweetTimes(adopters)
	callRfunctions(keyword)
	makeGIF(keyword, len(adopters))
	htmlString = makeHTML(keyword, tweets)
	saveAndLaunchHTML(htmlString, keyword)




# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
	main()







