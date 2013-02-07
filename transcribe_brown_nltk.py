import os
import subprocess

def clean_timit():
    '''cleans the timit selection sentence list available in NLTK
    '''
    corpus_dir = 'English/timit'
    f = open(os.path.join(corpus_dir, 'allsenlist.txt'), 'r').readlines()
    sents = open('timit.txt','w')
    for i in range(len(f)):
        sents.write(f[i].split('\t')[-1])
    sents.close()

def clean_sentences():
    '''cleans the annotations from the Brown corpus available from NLTK and saves
    the output to brown.txt. The contents of brown.zip should be in the directory 
    called corpus_dir

    http://nltk.googlecode.com/svn/trunk/nltk_data/packages/corpora/brown.zip
    '''
    corpus_dir = 'English/brown'
    files = sorted(os.listdir(corpus_dir))
    sents = open('brown.txt','w')
    for i in range(len(files)):
        if len(files[i]) == 4:
            f = open(os.path.join(corpus_dir, files[i]), 'r').readlines()
            for j in range(len(f)):
                clean = f[j].strip()
                if clean != '':
                    s = ''
                    l = clean.split()
                    for k in range(len(l)):
                        s += l[k].split('/')[0] + ' '
                    sents.write(s.strip()+'\n')

def transcribe():
    f = open('timit.txt', 'r').readlines()
    out = open('timit_trans.txt', 'w')
    t = len(f)
    for i in range(len(f)):
        if i % 10 == 0:
            print "transcribed %d of %d sentences" % (i, t)
        o = open('tmp', 'w')
        o.write(f[i])
        o.close()
        r = open('tmp','r')
        p = subprocess.Popen(["./text2phonesEN"], stdin=r, shell=True)
        p.wait()
        r.close()
        if os.path.isfile('segs.txt'):
            ph = open('segs.txt','r').readlines()
            os.remove('segs.txt')
            phones = []
            for k in range(len(ph)):
                phones.append(ph[k].strip().split(' ')[-1])
            #print f[i], '-'.join(phones)
            out.write("%d %s" %(i,f[i]))
            out.write("%d %s\n" %(i,'-'.join(phones)))
    out.close()

if __name__ == "__main__":
    transcribe()
