#!/usr/bin/python -tt

""" This file finds a list of common words and finds the angular simularity 
	between them """

import pickle
import re
import numpy as np
import MySQLdb as mdb
import math
import pandas as pd
import subprocess
import sys
import cgi


file = open("/Users/charlotte/Documents/2014/UNH TWITTER/commonWordsOnTwitter","r")
commonWords = [re.findall("[\w]+",c)[0] for c in file.readlines()]
file.close()

### returns dictionary of top W words
### they are mentioned at least ten times (as words not strings)
### chooses top W based on number of adopters
def getAdopters(W=700):
	print "Finding dictionary of the %s most commonly used words..."%W
	con = mdb.connect('localhost', 'testuser2', 'test623', 'TWITTER');
	cur = con.cursor()

	cur.execute("SELECT text FROM tweets")
	tweetsAll = cur.fetchall()

	words = {}

	for tweet in tweetsAll:
		newwords = re.findall("[\w\d]+",tweet[0].decode('utf-8').lower())
		if newwords:
			for word in np.unique(newwords):
				if len(word) > 2 and word not in commonWords[0:200]:
					if word in words:
						words[word] +=	1
					else:
						words[word] = 1

	## manually remove http,htt, https, amp (&), don (don't), via
	words['http'] = 0
	words['htt'] = 0
	words['https'] = 0
	words['amp'] = 0
	words['don'] = 0
	words['via'] = 0

	## words2 has words mentioned more than 10 times (not 10 adopters....)
	words2 = {}
	for word in words:
		if words[word] > 10:
			words2[word] = words[word]

	## number of adopters dictionary
	adopters = {}
	for word in words2:
		cur.execute("SELECT count(distinct(author_ID)) from tweets where lower(text) like '%"+word.encode('utf-8')+"%'")
		adopt1 = cur.fetchall()
		adopters[word] = adopt1[0][0]

	con.close()

	## reduce to top W
	def noAdoptersAsStrings(word):
		return adopters[word]
	
	topWordsAsStrings = sorted(adopters.keys(), key=noAdoptersAsStrings, reverse=True)[0:min(W, len(adopters.keys()))]
	for key in adopters.keys():
		if key not in topWordsAsStrings:
			adopters.pop(key,0)

	return adopters


### top words: number of adopters and peaks in adoptions (considering WORDS)
def getTopWords(adopters, N=100):
	print "Finding top tweets by number of adopters and growth in number of adopters..."

	peaks = {}
	noAdoptersAsWords = {}

	con = mdb.connect('localhost', 'testuser2', 'test623', 'TWITTER')
	cur = con.cursor()

#cur.execute("select screen_name,text from tweets")
#	tweets = cur.fetchall()

	for i in xrange(len(adopters.keys())):
		tweeted = []
		word = adopters.keys()[i]
		cur.execute("select text, id, screen_name from tweets where lower(text) like '%"+word+"%'")
		tweets = list(cur.fetchall())
		tweets2 = list(tweets)
		for tweet in tweets:
			newwords = re.findall("[\w\d]+",tweet[0].decode('utf-8').lower())
			if newwords:
				if tweet[2] in tweeted:
					tweeted += [tweet[2]]
					tweets2.remove(tweet)
				elif word not in newwords:
					tweets2.remove(tweet)
				else:
					tweeted += [tweet[2]]
		ids = [t[1] for t in tweets2]
		noAdoptersAsWords[word] = len(tweets2)
		peak = 0
		for id in ids:
			newPeak = sum([ i <= id + N and i >= id for i in ids])
			if newPeak > peak:
				peak = newPeak
		peaks[word] = peak

	con.close()

	def returnCount(item):
		return item[1]

	topWordsByAdopters = sorted(noAdoptersAsWords.items(), key=returnCount, reverse=True)[0:10]
	topWordsByPeaks = sorted(peaks.items(), key=returnCount, reverse=True)[0:10]

	return topWordsByAdopters, topWordsByPeaks


### Finding angular similarity matrix for a list of words
def angularSimilarity(words):
	print "Finding angularity similarity between words..."
	W = len(words)
	cosTop = np.zeros((W,W), dtype=np.int16)
	cosBottom = [0]*W

	con = mdb.connect('localhost', 'testuser2', 'test623', 'TWITTER');
	cur = con.cursor()

	for i in range(W):
		cur.execute("SELECT * FROM tweets WHERE lower(text) LIKE '%"+words[i]+"%'")
		iwords = cur.fetchall()
		if iwords:
			cosBottom[i] = len(iwords)
			for row in iwords:
				newwords = re.findall("[\w\d]+",row[3].decode('utf-8').lower())
				if words[i] in newwords:
					for j in range(W):
						if j != i:
							if words[j] in newwords:
								cosTop[i,j] += 1

	con.close()

	angularSim = np.zeros((W,W))
	for	i in range(W):
		for j in range(W):
			angularSim[i,j] = 1 - math.acos(cosTop[i,j]/float(np.sqrt(cosBottom[i]*cosBottom[j])))/math.pi

	return angularSim

### functions to find similar words/similarity between words
def simWords(word, words, angSim, minSim=0.52):
	index = 0
	W = len(words)
	for i in range(W):
		if words[i]==word:
			index=i
	simScores = angSim[index,]
	simWords = []
	for i in range(W):
		if simScores[i]>minSim:
			simWords += [words[i]]
	return simWords

def simBetweenWords(word1,word2, words, angSim):
	index1 = 0
	index2 = 0
	W = len(words)
	for i in range(W):
		if words[i]==word1:
			index1=i
		if words[i]==word2:
			index2=i
	return angSim[index1,index2]

### find words that are similar to top words, to include in word clouds
### use union of peaks and adopters
def similarToTopWords(words,topWords, angularSim, minSim=0.52):
	includedWords = []
	for i in range(len(words)):
		word = words[i]
		if word in [t[0] for t in topWords]:
			#print word, simWords(word)
			includedWords += simWords(word,words, angularSim, minSim=0.52)
			includedWords += [word]
	wordsToInclude = [w in includedWords for w in words]
	wordsToInclude = pd.Series(wordsToInclude)
	return wordsToInclude

### Reduce angular sim matrix to consider only words we want to include
### save as csv file.  Optionally return the matrix
### Also saves words to include in word cloud, along with number of adopters,
### and whether each word is a top word
def reduceAndSave(angularSim, wordsToInclude, adopters, topWords, minSim=0.52, returnMatrix=False):
	
	## reduce matrix
	y = pd.DataFrame(angularSim)
	angularSim = y[wordsToInclude].dropna(how="all").T.dropna(how="all").fillna(0)
	angularSim = angularSim[wordsToInclude]
	angularSim = angularSim[angularSim>minSim].fillna(0)
	angularSim = np.array(angularSim)
	W = angularSim.shape[0]

	noAd = list(pd.Series([int(adopters[word]) for word in adopters.keys()])[wordsToInclude])
	words = list(pd.Series(adopters.keys())[wordsToInclude])
	W = len(words)
	top = [0]*W

	for i in range(W):
		word = words[i]
		if word in [t[0] for t in topWords]:
			top[i] = 1

	## make string to save as csv file
	angularString = ""
	topWordsString = ""
	for i in range(W):
		topWordsString += words[i]+","+str(noAd[i])+","+str(top[i])+"\n"
		for j in range(W):
			angularString += str(angularSim[i,j])+","
		angularString += "\n"

	## save files
	file = open("/Users/charlotte/Documents/2014/UNH TWITTER/csvFiles/angularSim.csv", "w")
	file.write(angularString)
	file.close()

	file = open("/Users/charlotte/Documents/2014/UNH TWITTER/csvFiles/topWords.csv", "w")
	file.write(topWordsString)
	file.close()

	if returnMatrix:
		return angularSim, angularString


### Make graph in R

def makeGraph():
	print "Making graph in R..."
	subprocess.call("Rscript Rscripts/wordVisualisation.r", shell=True)

### Produce and save html

def makeHTML(topWordsByAdopters, topWordsByPeaks):
	print "Making html..."

	htmlString = """
		
		<!DOCTYPE html>
		<html>
		<head>
		<link rel="stylesheet" type="text/css" href="charlottestyle.css">
		</head>
		<body>
		<h1>What's trending at UNH?</h1>
		<div class="container" style="width:800px;margin-top:20px;min-height:450px;">
		<div style="width:550px;float:left;">
		<img src="../pics/wordsNew.png" style="width:450px;height:450px">
		</div>
		<div class="leftsection">
		<h3>Top words</h3>
		<div style="width:125px;float:left;"><h4>By number of tweeters</h4></br>
		<table id="mytable" style="width:100px;">
		"""
	for tweet in topWordsByAdopters:
		htmlString += "<tr><td>"+tweet[0]

		htmlString +="</td><td>"+str(tweet[1])+"</td></tr>"

	htmlString+= """
		</table>
		</div>
		<div><h4>By growth in number of tweeters</h4>
		<table id="mytable" style="width:100px;">"""
	for tweet in topWordsByPeaks:
		htmlString+= "<tr><td><a href='http://www.google.com'>"+tweet[0]+"</a></td><td>"+str(tweet[1])+"</td></tr>"

	htmlString+= """</table></div>
		</div>
		</div>
		</body>
		</html>
		"""

	file = open("html/trendsNew.html", "w")
	file.write(htmlString)
	file.close()

	subprocess.call("open -a Google\ Chrome html/trendsNew.html", shell=True)



def main():
	if len(sys.argv) > 1:
		W = int(sys.argv[1])
	else:
		W = 700

	adopters = getAdopters(W)
	topWordsByAdopters, topWordsByPeaks = getTopWords(adopters)
	topWords = topWordsByAdopters + topWordsByPeaks
	angSim = angularSimilarity(adopters.keys())
	wordsToInclude = similarToTopWords(adopters.keys(),topWords, angSim)
	reduceAndSave(angSim, wordsToInclude, adopters, topWords)
	makeGraph()
	makeHTML(topWordsByAdopters, topWordsByPeaks)



# This is the standard boilerplate that calls the main() function.
if __name__ == '__main__':
	main()




