# -*- coding: utf-8 -*-
"""
Created on Sun Sep 13 20:56:09 2020

@author: Kiera
"""

from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import nltk
import re
from re import search
import spacy
from spacy.matcher import Matcher

#String you want to see if anything matches
text = "What are the first names of students in their year"
nlp = spacy.load("en_core_web_sm")
def first_to_1(text):
    t = nltk.word_tokenize(text)
    numbers  = { 'first': 1, 'second':2, 'third' : 3}
    for x in t:
        for s in numbers:
            if s == x:
                return(numbers[s])
    return "X"

def numcheck(text):
    num = "X"
    NUMmatcher = Matcher(nlp.vocab)
    pattern= [{'ENT_TYPE': 'DATE' }]
    NUMmatcher.add("HelloWorld", None, pattern)
            

    doc = nlp(text)
    matches = NUMmatcher(doc)
    st = []
    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]
        st.append((str(doc[start:end])))
        span = doc[start:end] 
    if (len)(st) > 0:
        x = ' '.join(st)
        print(x)
      
        
    return num
   


print(numcheck(text))
 



    