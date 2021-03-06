import codecs
import sys
import operator
import math
import pylab
import os
import cPickle as pickle
from guppy import hpy
from apiclient.discovery import build
import time
import numpy as np

def makeSentenceList(filename, startID=0):
    '''creates a list of sentences that contains:
    ID: a unique 9 digit ID for the sentence
    lineno: the line number printed in the input file
    orth: the original Italian orthography
    phones: an ordered list of the phones in the sentence
    triphones: a dictionary containing the triphones and their counts

    returns sentences list as well as a dictionary containing counts for all 
    triphones in the input file
    '''
    f = codecs.open(filename, 'r', 'latin1').readlines()

    ID = startID
    total = {}
    sentences = []
    t = len(f)/2
    for i in range(0, len(f), 2):
        if i%200 == 0:
            sys.stdout.write("\rprocessing sentence %d of %d"%(i/2,t))
            sys.stdout.flush()
        triphones = {}
        orth = f[i][:-1]
        chunks = f[i+1].split()
        lineno = int(chunks[0])
        phones = chunks[1].split('-')
        phones.append('#') # add the last char
        for j in range(0,len(phones)-2):
            tri = '-'.join(phones[j:j+3])
            if triphones.has_key(tri):
                triphones[tri] += 1
            else:
                triphones[tri] = 1
            if total.has_key(tri):
                total[tri] += 1
            else:
                total[tri] = 1
        sentences.append(["%09d"%ID, lineno, orth, phones, triphones])
        ID += 1
    sys.stdout.write('\n')

    return sentences, total

def sortDict(dic):
    ''' reverse sorts a dictionary by value, returns a list'''
    sorted_dict = sorted(dic.iteritems(), key=operator.itemgetter(1), reverse=True)
    return sorted_dict

def makeTriphoneDict(sentences, triphone_dict):
    '''creates a dict of triphones with IDs of sentences that contain the triphone.
    This is slow
    '''
    triphones = sorted(triphone_dict.keys())
    output = {}
    t = len(triphones)
    for i in range(len(triphones)):
        if i % 10 == 0:
            sys.stdout.write("\rprocessing triphone %d of %d" % (i,t))
            sys.stdout.flush()
        ids = []
        tri = triphones[i]
        for j in range(len(sentences)):
            if sentences[j][-1].has_key(tri):
                ids.append(sentences[j][0])
        output[tri] = ids
    sys.stdout.write('\n')
    return output

def scoreSentences(sentences, total):
    '''Scores the sentences for phonetic density
    '''
    triphone_scores = {}
    ranked = sortDict(total)
    N = 0 # the total number of triphones
    for (i,j) in ranked:
        N += j
    for (i,j) in ranked:
        freq = j/float(N) 
        neglogfreq = -math.log(freq) 
        triphone_scores[i] = neglogfreq
    t = len(sentences)
    for i in range(len(sentences)):
        if i %100 == 0:
            sys.stdout.write("\rprocessing sentence %d of %d" %(i,t))
            sys.stdout.flush()
        nphones = len(sentences[i][3])
        tris = sentences[i][-1].items()
        nuniq = len(tris)
        scores = []
        for (k,v) in tris:
            scores.append(v*triphone_scores[k])
        # sum(scores)/nphones: average neglogfreq per phone
        # nuniq/nphones: rewards more variety of triphones
        rating = (sum(scores)/nphones) * (float(nuniq)/nphones)
        sentences[i].append(rating)
    sys.stdout.write('\n')
    ranked = sorted(sentences, key=operator.itemgetter(-1), reverse=True)
    return ranked

def rankPlots(total, ranked_scores=None):
    ranked_triphones = sortDict(total)
    rank = range(1,len(ranked_triphones)+1)
    count = []
    for i in range(len(ranked_triphones)):
        count.append(ranked_triphones[i][1])
    fig = pylab.figure('triphoneRank')
    ax = fig.add_subplot(111)
    pylab.plot(rank, count, '-')
    ax.set_yscale('log')
    pylab.ylabel('(log) Occurrences')
    pylab.xlabel('Rank')
    pylab.title('Triphone occurrences vs. rank')
    pylab.savefig('triphone_ranks.jpg')

    fig2 = pylab.figure('scores')
    ax = fig2.add_subplot(111)
    count = []
    for i in range(len(ranked_scores)):
        count.append(ranked_scores[i][-1])
    n, bins, patches = ax.hist(count, 50, normed=1, facecolor='gray', alpha=0.85)
    ax.set_xlabel('Score')
    ax.set_ylabel('Probability')
    ax.set_title('Distribution of scores')
    pylab.savefig('score_dist.jpg')

    if ranked_scores is not None:
        rank = range(1,len(ranked_scores)+1)
        pylab.figure('scoreRank')
        pylab.plot(rank,count, '-')
        pylab.ylabel('Score')
        pylab.xlabel('Rank')
        pylab.title('Sentence score vs. rank')
        pylab.savefig('score_ranks.jpg')

def getScores(IDs, sentences):
    '''returns scores for each ID in the the input list'''
    scores = []
    for i in range(len(IDs)):
        ind = int(IDs[i])
        score = sentences[ind][-1]
        scores.append((ind,score))
    scores = sorted(scores, key=operator.itemgetter(1), reverse=True)
    return scores

def selectBestSubset(nsentences, sentences, total, tridict, apikey=None):
    '''Selects the best nsentences from the set of sentences.
    "Best" in terms of phonetic density
    Proceedure:
    start: find highest-ranked triphone with 0 occurances in the master count list
    find highest-ranked sentence containing that triphone
    add triphone counts of chosen sentence to master count list
    repeat nsentences times
    threshold - if there are no more triphones with 0 occurances above thresh,
    choose the triphone with lowest number of occurances
    '''
    #threshold = 10 #triphones with fewer than 10 occurances in the corpus not used
    #ranked_sentences = sorted(sentences, key=operator.itemgetter(-1), reverse=True)
    ranked_triphones = sortDict(total)
    
    master_count = {}
    for i in range(len(ranked_triphones)):
        master_count[ranked_triphones[i][0]] = 0
    selected = []
    selected_inds = []
    indfile = open('used_inds.csv','w')
    selfile = codecs.open('selected.txt', 'w', 'latin1')
    for i in range(nsentences):
        sys.stdout.write('\rfound %d of %d sentences'%(i, nsentences))
        sys.stdout.flush()
        # find first unused triphone
        nokey = True
        j = 0
        while nokey and (j<len(ranked_triphones)):
            k = ranked_triphones[j][0]
            if master_count[k] == 0:
                scores = getScores(tridict[k], sentences)
                # find first unused sentence
                nosent = True
                l = 0
                while nosent and (l<len(scores)):
                    ind = scores[l][0]
                    if ind not in selected_inds:
                        selected_inds.append(ind)
                        # check that it is Italian
                        if apikey is not None:
                            st = sentences[ind][2]
                            if ':' in st:
                                st = st.split(':')[-1]
                            if len(st) <= 150:
                                lang, conf = checkLanguage(st,apikey)
                                indfile.write("%d,%s,%f\n"%(ind,lang,conf))
                                if lang == 'it':
                                    selfile.write('%d %s\n'%(ind,st))
                                    selected.append(sentences[ind])
                                    nosent = False
                                    nokey = False
                        else: # if there is no apikey, just add regardless of lang
                            selected.append(sentences[ind])
                            nosent = False
                            nokey = False
                    l += 1
            j += 1
        #update master_count
        sel_tris = selected[-1][4].items()
        for t,c in sel_tris:
            master_count[t] += c         
    sys.stdout.write('\n')
    selfile.close()
    indfile.close()
    return selected, selected_inds, master_count

def checkLanguage(sentence, apikey):
    '''Uses the google translate api to detect the language of the candidate sentence
    Requires an active google api key ($)
    '''
    time.sleep(1) # google sets user rate limit that is easily exceeded
    service = build('translate', 'v2', developerKey=apikey)
    response = service.detections().list(q=[sentence]).execute()
    lang = response['detections'][0][0]['language']
    conf = response['detections'][0][0]['confidence']
    return lang, conf


def getTotals():
    '''The transcriptions can be done in chunks to enable parallelism. 
    This function combines the parts to get the total triphone count, assuming that 
    transcribed files have been saved as trans001.txt, trans002.txt, etc.
    '''
    total = {}
    files = sorted(os.listdir('.'))
    trans = []
    for i in files:
        if i[:5] == 'trans' and i[-3:] == 'txt':
            trans.append(i)
    ID = 0
    h = hpy()
    for i in range(7):
        print h.heap()
        sents, tot = makeSentenceList(trans[i], ID)
        ID = int(sents[-1][0])+1
        for k,v in tot.items():
            if total.has_key(k):
                total[k] += v
            else:
                total[k] = v
        del sents
        del tot
    return total

def findIndex(n):
    '''This function finds the ID number of the first sentence in chunk n of the 
    transcription files, For example looking for the ID of the first sentence in
    trans3.txt
    '''
    ID = 0
    for i in range(1, n):
        f = codecs.open('trans%d.txt'%i, 'r','latin1').readlines()
        nsents = len(f)/2
        ID += nsents
    return ID

def randomSample(n, sentences, total, apikey=None):
    '''This function randomly samples n sentences comparible to those which are
    chosen by selectBestSubset, in order to compare the distributions of the results
    '''
    inds = np.arange(len(sentences))
    np.random.shuffle(inds)
    selected = []
    ranked_triphones = sortDict(total)
    master_count = {}
    for i in range(len(ranked_triphones)):
        master_count[ranked_triphones[i][0]] = 0
    nsents = 0
    current = 0
    while nsents < n:
        sys.stdout.write('\rfound %d of %d sentences'%(nsents, n))
        sys.stdout.flush()
        foundSent = False
        while not foundSent:
            st = sentences[inds[current]][2]
            if ':' in st:
                st = st.split(':')[-1]
            if len(st) <= 150:
                if apikey is not None:
                    lang, conf = checkLanguage(st, apikey)
                    if lang == 'it':
                        selected.append(sentences[inds[current]])
                        foundSent = True
                        nsents += 1
                else:
                    selected.append(sentences[inds[current]])
                    foundSent = True
                    nsents += 1
            current += 1
        sel_tris = selected[-1][4].items()
        for t,c in sel_tris:
            master_count[t] += c         
    sys.stdout.write("\n")
    return selected, master_count

def compareEnglish():
    '''This function uses the brown and timit sentences from NLTK to compare the 
    distributions of a hand-crafted corpus (timit) to the automatically generated
    one made with selectBestSubset
    This depends on the files 'brown_trans.txt' and 'timit_trans.txt' created with
    transcribe_brown_nltk.py
    '''
    sents1, total = makeSentenceList('brown_trans.txt',0)
    selected, total2 = makeSentenceList('harvard_trans.txt',len(sents1))
    for k,v in total2.items():
        if total.has_key(k):
            total[k] += v
        else:
            total[k] = v
    ranked_triphones = sortDict(total)
    rank = range(1,len(ranked_triphones)+1)
    count = []
    selcount = []
    for i in range(len(ranked_triphones)):
        count.append(ranked_triphones[i][1])
        if total2.has_key(ranked_triphones[i][0]):
            selcount.append(total2[ranked_triphones[i][0]])
        else:
            selcount.append(0)
    fig = pylab.figure('triphoneRank')
    ax = fig.add_subplot(111)
    pylab.plot(rank, count, 'b-')
    pylab.plot(rank, selcount, 'g-')
    ax.set_yscale('log')
    pylab.ylabel('(log) Occurrences')
    pylab.xlabel('Rank')
    pylab.title('Triphone occurrences vs. rank (Brown/Harvard)')
    pylab.savefig('harvard_ranks.jpg')
   
def makeResultsPlot(total, selected_total, outname):   
    ranked_triphones = sortDict(total)
    rank = range(1,len(ranked_triphones)+1)
    count = []
    selcount = []
    for i in range(len(ranked_triphones)):
        count.append(ranked_triphones[i][1])
        if selected_total.has_key(ranked_triphones[i][0]):
            selcount.append(selected_total[ranked_triphones[i][0]])
        else:
            selcount.append(0)
    fig = pylab.figure('triphoneRank')
    ax = fig.add_subplot(111)
    pylab.plot(rank, count, 'b-')
    pylab.plot(rank, selcount, 'g-')
    ax.set_yscale('log')
    pylab.ylabel('(log) Occurrences')
    pylab.xlabel('Rank')
    pylab.title('Triphone occurrences vs. rank')
    pylab.savefig(outname)

def threshold(selected, total, thresh):
    '''Checks to see if each sentence in selected has triphones that occur less
    than 'thresh' times in the corpus (total). Returns sentences that do not have 
    triphones below threshold.
    '''
    valid = []
    for i in range(len(selected)):
        passed = True
        tris = selected[i][4].items()
        for k,v in tris:
            if total[k] < thresh:
                passed = False
                break
        if passed:
            valid.append(selected[i])
    return valid

def countTriphones(selected):
    counts = {}
    for i in range(len(selected)):
        item_list = selected[i][4].items()
        for k,v in item_list:
            if counts.has_key(k):
                counts[k] += v
            else:
                counts[k] = v
    return counts

def demo(filename):
    '''This function shows how all the other functions work together
    filename input is a txt file with transcriptions
    '''
    # sentences contains ID, original line number, orthography, phones list, and 
    # triphones list for each sentence in the input file
    # total contains triphone counts for every triphone in the input
    sentences, total = makeSentenceList(filename)

    # tridict: keys are triphones, values are lists of IDs of sentences with that triphone
    if os.path.isfile('tridict1.pkl'):
        tridict = pickle.load(file('tridict1.pkl','rb'))
    else:
        tridict = makeTriphoneDict(sentences, total)

    # at this point we can get a better set of triphone counts using more data
    if os.path.isfile('counts1-7.pkl'):
        total = pickle.load(file('counts1-7.pkl', 'rb'))
    else:
        total = getTotals()

    # score the sentences - the scores are added to the sentences list
    # ranked is basically useless unless we want to do the plots
    # more sentences could be added to the sentences list, but memory becomes an issue
    ranked = scoreSentences(sentences, total)

    # create the rank plots
    rankPlots(total, ranked)

    # pick a subset
    #selected, inds, counts = selectBestSubset(100, sentences, total, tridict)
    #f = codecs.open('selected.txt', 'w', 'latin1')
    #for i in selected:
    #    f.write(i[2]+'\n')
    #f.close()

def demo_lit_corpus(nsent=1800, thresh=9):
    sentences, total = makeSentenceList('all_trans.txt')
    if os.path.isfile('litcorpus_tridict.pkl'):
        tridict = pickle.load(file('litcorpus_tridict.pkl','rb'))
    else:
        tridict = makeTriphoneDict(sentences, total)
    ranked = scoreSentences(sentences, total)
    selected, inds, counts = selectBestSubset(nsent, sentences, total, tridict)
    valid = threshold(selected, total, thresh)

    #write out the orthography and transcriptions to a tsv file
    o = codecs.open('lit_corpus_candidates.tsv', 'w', 'latin1')
    for i in range(len(valid)):
        o.write("%s\t%s\t%s\n" %(valid[i][0], valid[i][2], '-'.join(valid[i][3])))
    o.close()

if __name__ == "__main__":
    #demo(sys.argv[1])
    #total = getTotals()
    #pickle.dump(total, file('counts1-7.pkl','wb'))
    #compareEnglish()
    if len(sys.argv) == 1:
        demo_lit_corpus()
    else:
        demo_lit_corpus(int(sys.argv[1]), int(sys.argv[2]))

