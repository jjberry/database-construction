import codecs
import sys
import operator
import math
import pylab

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

def rankPlots(total, ranked_scores):
    ranked_triphones = sortDict(total)
    rank = range(1,len(ranked_triphones)+1)
    count = []
    for i in range(len(ranked_triphones)):
        count.append(ranked_triphones[i][1])
    fig = pylab.figure('triphoneRank')
    ax = fig.add_subplot(111)
    pylab.plot(rank, count, '-')
    ax.set_yscale('log')
    pylab.ylabel('(log) Occurances')
    pylab.xlabel('Rank')
    pylab.title('Triphone occurances vs. rank')
    pylab.savefig('triphone_ranks.jpg')
    
    rank = range(1,len(ranked_scores)+1)
    count = []
    for i in range(len(ranked_scores)):
        count.append(ranked_scores[i][-1])
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

def selectBestSubset(nsentences, sentences, total, tridict):
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
    for i in range(nsentences):
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
                        selected.append(sentences[ind])
                        nosent = False
                        nokey = False
                    l += 1
            j += 1
        #update master_count
        sel_tris = selected[-1][4].items()
        for t,c in sel_tris:
            master_count[t] += c

    return selected, selected_inds, master_count



