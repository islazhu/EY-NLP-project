from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import nltk
import re
from re import search
import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm")


## Test queryes
Testing = "What are the lastname of students with GPA greater than 3.0"
T = "Where age is above 21"
H = "How many female in the class"
E = "What is the GPA of Mike"

# I have been able to get the column names from the csv file in the project so I feel comfortable hardcoding it here for the time being.
# ISSUE: Obviously no one would type lastname they would type last name  so this is one fix I need to make
column_names =  ("firstname", "lastname", "GPA", "email", "year")
table_names = ("students")


#Look at each word in the query and if they are a noun add them to a list.
#If that noun is also a column heading  add it to the final list.
def nounlist(query):
    nounlist = []
    fn = []
    tn = []
    nn = []
    text = word_tokenize(query)
    y = nltk.pos_tag(text)
    for x in y:
        if "NNS" == x[1]  or "NN"  == x[1] or  "NNP"  == x[1]:
            nounlist.append(x[0])
        
    for x in nounlist:
        if x in column_names and  x not in fn:
            fn.append(x)
        elif x in table_names and x not in tn: 
            tn.append(x)
        else:
            nn.append(x)
            
    return (fn,tn,nn)
         
    #
    
 
def Chunk(text):  
    #Text is our query
    #chunkGram is the pattern we want to look for.
    # JJR = comparative adjective   IN = Preposition  CD = cardinal numeral IN = Infinite Marker To
    chunkGram = """Chunk: {(<JJR>* <IN>+ <CD>+) |(<JJ>)* <TO>+ <CD>+} """
    #Splitting query into words
    ext = word_tokenize(text)
    #POS each word
    ty = nltk.pos_tag(ext)
    print(ty)
    chunkParser = nltk.RegexpParser(chunkGram)
    chunked = chunkParser.parse(ty)
    c = []
    return chunked





def generate_select ( text ):
    Selected = " "
    Select = " "
    Countmatcher = Matcher(nlp.vocab)
    pattern = [{'POS': 'ADJ', 'TAG': 'JJ'},
           {'POS': 'NOUN', 'TAG': 'NN'}]
    pattern1 = [{'POS': 'ADV', 'TAG': 'WRB'},
           {'POS': 'ADJ', 'TAG': 'JJ'}]
    Countmatcher.add("HelloWorld", None, pattern1)
    Countmatcher.add("HelloWorld", None, pattern)

    doc = nlp(text)
    matches = Countmatcher(doc)
    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end] 
    if ((len(matches)) > 0):
        Selected = "COUNT(*) "
    # If we are not looking for the count then look for the columns aka nouns in the query.
    else:
         mylist = []
         li = nounlist(text)[0]
        
         my_string = ','.join(li)
            
         Selected = Selected + my_string
    
    Select = "SELECT  " + Selected
    
    return(Select)

def generate_from ( text ):
    # If I have extra time I will get the table names like I got the column names and then we can say this is generated and not hard coded.
    Froms = " "
    From =  " FROM " + "Students "
    return From

def generate_where ( text ):
    where = ""
    match = 2
    nlp = spacy.load("en_core_web_sm")

    OPmatcher = Matcher(nlp.vocab)
        
    #WHERE  YEAR(noun) IS(aux) 3(num)
    patternS = [{'POS': 'NOUN'},
               {'POS': 'AUX'},
               {'ORTH': 'not', 'OP': '?'},
                {'POS': 'NUM'}]

    patternY = [{'POS': 'NOUN'},
           {'POS': 'AUX'},
           {'POS': 'ADJ'},
           {'POS': 'ADP'},
           {'POS': 'NUM'}]

    pattern = [{'POS': 'NOUN'},
               {'POS': 'AUX'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]

    patternB= [{'POS': 'PROPN'},
               {'POS': 'AUX'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]
    patternC =[
               {'POS': 'NOUN'},
               {'POS': 'AUX'},
               {'POS': 'ADP'},
               {'POS': 'NUM'}]
    patternD =[{'POS': 'NOUN'},
               {'POS': 'AUX'},
               {'POS': 'ADP'},
               {'POS': 'NUM'}]
    patternF =[
               {'POS': 'NOUN'},
               {'POS': 'ADJ'},
               {'POS': 'ADP'},
               {'POS': 'NUM'}]
    patternE =[
               {'POS': 'NOUN'},
               {'POS': 'VERB', 'TAG': 'VBZ'},
               {'POS': 'NUM'}]
    patternZ =[{'POS': 'PROPN'},
                {'POS': 'AUX'},
                {'POS': 'ADP'},
                {'POS': 'NUM'}]
    OPmatcher = Matcher(nlp.vocab)
    OPmatcher.add("HelloWorld", None, pattern)
    OPmatcher.add("HelloWorld", None, patternC)
    OPmatcher.add("HelloWorld", None, patternB)
    OPmatcher.add("HelloWorld", None, patternD)
    OPmatcher.add("HelloWorld", None, patternE)
    OPmatcher.add("HelloWorld", None, patternF)
    OPmatcher.add("HelloWorld", None, patternZ)
    OPmatcher.add("HelloWorld", None, patternS)
    OPmatcher.add("HelloWorld", None, patternY)
  
    
    
    doc = nlp(text)
    matches = OPmatcher(doc)
    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end] 
    if ((len(matches)) > 0):
        
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(str(span))
        for token in doc:
            if token.pos_ == "NOUN" or  token.pos == "PROPN":
                W = token.text
        
        doc1 = nlp(str(span))
        for token in doc1:
            if token.pos_ == "ADP" or  token.pos_ == "ADJ" or token.pos_ == "VERB":
                o = token.text
            if token.pos_ == "NUM":
                num = token.text
            if token.text == "not":
                where = "Where not"
                
        
        x = ['below' , 'less', 'fewer', 'lower']
        z = ['greater', 'more', 'higher']
        op = " "
        
        if o in x:
             op = "<"
        elif o in z:
            op = ">"
        else: 
            op = "="
        
        
    
        return(where)
        match = match - 1
  
    else: 
        return( "No pattern ")


def generateSQL(text):
    print(text)
    sql = generate_select(text) + generate_from(text) + generate_where(text)
    return sql

# This tests that our how many pattern works 
print(generateSQL(" How many students where  year is above 3"))

# This tests that our noun select pattern works
# print(generateSQL(E))

# This tests that our operational where pattern works with greater than 3 (3 words)
#print(Chunk(Testing))

# This tests that our operational where pattern works with above 21 (2 words)
#print(Chunk(T))