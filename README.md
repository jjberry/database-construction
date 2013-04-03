database-construction
=====================

Tools for the construction of an articulatory speech database.

Starting from a plain text corpus, such as a cleaned wikipedia dump, these
tools are designed to help the user create a phonetically balanced list of
sentences to use as prompts for data collection. The tools were developed for
Italian, using the PAISA plain text corpus as the starting point
http://www.corpusitaliano.it/en/index.html

Contents
========
text2phones: a scheme script for Italian transciptions using Festival
http://www.cstr.ed.ac.uk/projects/festival/

transcribe.py: designed to clean the raw PAISA text and call text2phones to
produce transcriptions

triphones.py: contains utilities for collecting statistics on the
transcriptions and picking a subset of sentences for best phonetic coverage.
Optionally uses the Google Translate API for language verification, since PAISA
contains some sentences in other languages, mostly English.

Also included are transcribebrownnltk.py and text2phonesEN for testing the 
algorithm on English data sets.

The file all_trans.tar.gz is a sample database of Italian sentences taken from
classic novels. Included in the triphones.py script is a demo that makes use of 
this database. To run the demo, first uncompress the file.
