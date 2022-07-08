# -*- coding: utf-8 -*-
"""
Created on Sat Sep 12 21:48:54 2020

@author: Kiera
"""

import spacy

nlp = spacy.load("en_core_web_sm")
doc = nlp("What GPAs of students are above 4")




for token in doc:
    print(token.text, token.pos_, )
           