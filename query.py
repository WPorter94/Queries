import os
import sys
import gzip
import json
import csv
import time
import math
def main():
    
    argv_len = len(sys.argv)
    inputFile = sys.argv[1] if argv_len >= 2 else 'shakespeare-scenes.json.gz'
    queriesFile = sys.argv[2] if argv_len >= 3 else 'trainQueries.tsv'
    outputFile = sys.argv[3] if argv_len >= 4 else 'train.results'

    with gzip.open(inputFile) as unzippedFile:
        fileData = json.load(unzippedFile)
        fileData = fileData["corpus"]
    invertedIndex, totalDocuments, documentOccurences, documentLengths, averageDL, docNM = evaluateDoc(fileData)
    if os.path.exists(outputFile):
        os.remove(outputFile)
    k1 = 1.8 
    k2 = 5
    b = 0.75
    mu = 300
    with open(queriesFile) as queries:
        queriesData = csv.reader(queries,delimiter="\t")
        for row in queriesData:
            itr1 = 1
            time1 = time.perf_counter()
            a = evaluateQuery(row, k1,k2,b,averageDL,totalDocuments,documentOccurences,documentLengths, invertedIndex,docNM,mu)
            opFile = open( outputFile,'a')
            for i in a:
                if itr1 > 100:
                    break
                temp = "{:.6f}".format(a[i])
                opFile.write(row[0] + " skip " + docNM[i]+ " " + str(itr1) + " "+ str(temp) + " Porter"  "\n")
                itr1 += 1
            time2 = time.perf_counter()
            print(row[0],time2-time1)

def evaluateQuery(row, k1,k2,b,averageDL,totalDocuments,documentOccurences,documentLengths, invertedIndex,docNM,mu):
    ql = True
    number = 0
    scene = 0
    wordsToFind = []
    totalVal = 0
    returnedVal = {}
    queryFreq ={}
    collectionTotalTerms = sum(documentLengths.values())
    
    for word in row:
        if number == 0:
            query = word
        elif number == 1:
            sceneOrPlay = word
        elif number == 2:
            if word == "ql":
                ql = True
            elif word == "bm25":
                ql = False     
        else: 
            if word in queryFreq:
                queryFreq[word] = queryFreq.get(word) + 1
                if query == "query7a":
                    print(queryFreq)
            else:
                queryFreq[word] = 1
            wordsToFind.append(word)
        number += 1
    if ql == False:
        wordsToFind = set(wordsToFind)
    #queryReleventDocs = getqueryReleventDocs(wordsToFind, invertedIndex)
    while scene < totalDocuments:
        totalVal = 0
        sceneCount = 0
        for term in wordsToFind:
            if ql == False:
                if scene in invertedIndex[term]:
                    totalVal += getBM25(k1,k2, b, averageDL, documentLengths[scene], documentOccurences[term], invertedIndex[term][scene], totalDocuments,queryFreq[term])
                    sceneCount+= 1
            else:
                collectionTermOccurences = sum(invertedIndex[term].values())
                if scene in invertedIndex[term]:
                    totalVal += getq1(invertedIndex[term][scene], mu, collectionTermOccurences, collectionTotalTerms,documentLengths[scene]  )
                    sceneCount+=1
                else:
                    totalVal += getq1(0, mu, collectionTermOccurences, collectionTotalTerms,documentLengths[scene]  )
        if totalVal != 0 and sceneCount > 0:
            returnedVal[scene] = round(totalVal,6)
        scene += 1
   
    return dict(sorted(returnedVal.items(), key = lambda item: item[1], reverse=True))

def getq1(qinD, mu, qinC, winC, winD):
    q1 = math.log((qinD + mu * qinC / winC)/ (winD + mu))
    return q1

def getBM25(k1,k2, b, avgDL, documentL, docOccurences, thisDocOccurences, totalDocs, queryFreq):
    K = getK(k1,b,avgDL,documentL)
    N = totalDocs
    ni = docOccurences
    bpm = math.log((N- ni + .5)/(ni  + .5))
    #bpm = (1)/(ni  + .5)/(N- ni + .5)
    tfDoc = ((k1+1) * thisDocOccurences)/(K + thisDocOccurences)
    tfQuery = ((k2 +1)*queryFreq)/(k2 + queryFreq)
    return bpm*tfDoc*tfQuery

def getK(k1, b, avgDL, dL):
    K = k1 * ((1-b)+b*dL/avgDL)
    print(K)
    return K

def getPlayId(sNum,fd):
    for i in fd:
        if i["sceneNum"] == sNum:
            return i["playId"]

def getSceneId(sNum,fd):
    for i in fd:
        if i["sceneNum"] == sNum:
            return i["sceneId"]

def getqueryReleventDocs(wordsToFind, invertedIndex):
    totalQrelevancy = 0
    addedList = []
    for term in wordsToFind:
        IIkeys = invertedIndex[term].keys()
        for marker in IIkeys:
            if marker not in addedList:
                addedList.append(marker)
    return len(addedList)

def evaluateDoc(fd):
    il = {}
    docOccurences = {}
    docLengths = {}
    totalDocs = 0
    avgLength = 0
    docNumName = {}

    for i in fd:
        totalDocs += 1
        tokenizedWords = i["text"].split()
        count = 0
        #length of each document
        docLengths[i["sceneNum"]] = len(tokenizedWords)
        docNumName[i["sceneNum"]] = i["sceneId"]
        avgLength += len(tokenizedWords)
        for uniqueToken in set(tokenizedWords):
            #(docOccurences) counts total docs that contain term
            if uniqueToken in docOccurences:
                docOccurences[uniqueToken] = docOccurences.get(uniqueToken) + 1
            else:
                docOccurences[uniqueToken] = 1
            #(il) counts number of term occurences in each individual document
            count = tokenizedWords.count(uniqueToken)
            if uniqueToken in il.keys():               
                il[uniqueToken].update({i["sceneNum"]:count})
            else:            
                il[uniqueToken] = {i["sceneNum"]:count}
    avgLength = avgLength / len(fd)  

    return il, totalDocs, docOccurences, docLengths, avgLength, docNumName

""" def evaluate(r,ii,fd):
    foundScenes = []
    wordIndex = []
    foundPhrases = []
    sceneOrPlay = ""
    finalList = []
    andFlag = False
    orFlag = False
    number = 0
    for word in r:
        if number == 0:
            print()
        elif number == 1:
            sceneOrPlay = word
        elif number == 2:
            if word == "and":
                andFlag = True
            elif word == "or":
                orFlag = True
        elif " " in word:
            newWords = word.split()
            for newWord in newWords:
                if newWord in ii.keys() :   
                    tempIndex = ii[newWord]
                else:
                    tempIndex=[]               
                if wordIndex == []:
                    wordIndex = tempIndex
                else:
                    consecutiveWordIndex = []
                    for i in tempIndex:
                        for j in wordIndex:
                            if i[0] == j[0]:
                                if i[1] - j[1] == 1:
                                    consecutiveWordIndex.append(i)
                    wordIndex = consecutiveWordIndex
            foundPhrases.append(wordIndex)        
        else:
            if word in ii.keys(): 
                foundPhrases.append(ii[word])
        number += 1
    for el in foundPhrases:
        placeholder = []
        for i in el:
            if sceneOrPlay == "play":
                id = getPlayId(i[0],fd)
                if id not in placeholder:
                    placeholder.append(id)
            else: 
                id = getSceneId(i[0],fd)
                if id not in placeholder:
                    placeholder.append(id)
        foundScenes.append(placeholder)

    if andFlag == True:
        for tag in foundScenes:
            for i in tag:
                inAll = True
                for tag2 in foundScenes:
                    if i not in tag2:
                        inAll = False
                if inAll == True and i not in finalList:
                    finalList.append(i)               
    else: 
        for tag in foundScenes:
            for i in tag:
                finalList.append(i)  
    return finalList
 """

"""def count(fd):
    numElements= len(fd)
    totalLength = 0
    longestS = 0
    longestSName= ""
    shortestS = 1000000
    shortestSName=""
    lastPlay = ""
    playTotalLength = 0
    shortestP = 100000000
    shortestPName = ""
    longestP = 0
    longestPName= ""
    playLengths = []
    playNames = []
    for i in fd:

        tempLength = len(i["text"])
        totalLength += tempLength
        if len(i["text"]) < shortestS:
            shortestS = len(i["text"])
            shortestSName = i["sceneId"]
        if len(i["text"]) > longestS:
            longestS = len(i["text"])
            longestSName = i["sceneId"]
    for i in fd:
        
        if lastPlay == "":
            lastPlay = i["playId"]
        if lastPlay != i["playId"]:
            playLengths.append(playTotalLength)
            playNames.append(i["playId"])
            playTotalLength = 0
            lastPlay = i["playId"]
        playTotalLength += len(i["text"])
    playLengths.append(playTotalLength)
    playNames.append(i["playId"])

    for i, num in enumerate(playLengths):
        if num > longestP:
            longestP = num
            longestPName = playNames[i]
        if num < shortestP:
            shortestP = num
            shortestPName = playNames[i]

        
            

    average = (totalLength / numElements)    
    print(average,longestSName,shortestSName,longestPName,shortestPName)
"""
main()
