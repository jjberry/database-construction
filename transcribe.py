import subprocess
import codecs
import sys, os
import re

def transcribe(filename, outfile):
    f = codecs.open(filename, 'r', 'latin1').readlines()
    out = codecs.open(outfile, 'w', 'latin1')
    t = len(f)
    for i in range(len(f)):
        if i % 10 == 0:
            print "transcribed %d of %d sentences" % (i, t)
        o = codecs.open('tmp', 'w', 'latin1')
        o.write(f[i])
        o.close()
        r = open('tmp','r')
        p = subprocess.Popen(["text2phones"], stdin=r)
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


def clean(filename, outfile):
    f = codecs.open(filename, 'r', 'utf_8').readlines()
    o = codecs.open(outfile, 'w', 'latin1')
    for i in range(len(f)):
        if f[i][0] not in '#<':
            sentences = re.split(r'[.;] ', f[i][:-1])
            for j in range(len(sentences)):
                if sentences[j] != '':
                    clean = ''
                    for c in sentences[j]:
                        if ord(c) < 256:
                            clean += c
                    o.write(clean+'\n')
    o.close()


if __name__ == "__main__":
    transcribe(sys.argv[1], sys.argv[2])
    #clean(sys.argv[1], sys.argv[2])

