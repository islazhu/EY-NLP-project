import time, os
from flask import Flask, render_template, flash, redirect, request, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask import send_from_directory
from sqlalchemy.sql import text
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists
import sqlalchemy_utils
from sqlalchemy import MetaData
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
import sqlalchemy.types as types
import sqlalchemy
from nltk.tokenize import word_tokenize
import nltk
import ssl
import re
import csv
import spacy
from spacy.matcher import Matcher
from nltk.stem import WordNetLemmatizer
import pandas as pd
from datetime import datetime, timedelta
from word2number import w2n
from werkzeug.utils import secure_filename
import stringcase


import random
#Global variable that is False unless a csv file has been uploaded.
global upload_status

upload_status = False
debugMode = False
#This was added to fix issues when trying to import libraries from the dockerfile
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
nlp = spacy.load("en_core_web_sm")

nltk.download('punkt')
nltk.download('wordnet')
nltk.download('averaged_perceptron_tagger')
app = Flask(__name__)
app.config['SECRET_KEY'] = 'nh489fhf40fh0w083hf41ng4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD'] = 'data/current'

global sql_keywords
global sql_symbols 

# List of sql keywords and symbols that if entered into a query may stop it from running as the user expects.
sql_symbols = ['/', '.']
sql_keywords = ['abort', 'add', 'after', 'all', 'alter', 'analyze', 'and', 'as', 'asc', 'attach', 'autoincrement', 'before', 'begin', 'between', 'by', 'cascade', 'case', 'cast', 'check', 'collate', 'column', 'commit', 'conflict', 'constraint', 'create', 'cross', 'current_date', 'current_time', 'current_timestamp', 'database', 'default', 'deferrable', 'deferred', 'delete', 'desc', 'detach', 'distinct', 'drop', 'each', 'else', 'end', 'escape', 'except', 'exclusive', 'exists', 'explain', 'fail', 'for', 'foreign', 'from', 'full', 'glob', 'group', 'having', 'if', 'ignore', 'immediate', 'in', 'index', 'indexed', 'initially', 'inner', 'insert', 'instead', 'intersect', 'into', 'is', 'isnull', 'join', 'key', 'left', 'like', 'limit', 'match', 'natural', 'not', 'notnull', 'null', 'of', 'offset', 'on', 'or', 'order', 'outer', 'plan', 'pragma', 'primary', 'query', 'raise', 'references', 'regexp', 'reindex', 'release', 'rename', 'replace', 'restrict', 'right', 'rollback', 'row', 'savepoint', 'select', 'set', 'table', 'temp', 'temporary', 'then', 'to', 'transaction', 'trigger', 'union', 'unique', 'update', 'using', 'vacuum', 'values', 'view', 'virtual', 'when', 'where']
global column_selected
column_selected = []


def database_initialization_sequence(filename):
    # This function creates the database from the .csv
    global engine
    global dbfile
    global inspector
    global tablelist
    global columnlist
    global columnnamelist
    global columntypelist
    global column_selected
    global current_dbfile
    global database
    global keywords_in_columns	

    dbfile = ''	
    inspector = ''	
    tablelist = []	
    columnlist = []	
    columnnamelist = []	
    columntypelist = []
    keywords_in_columns = []
    

    	
   
    
#https://www.dataquest.io/blog/sql-insert-tutorial/
    # directory of where the file is stored when uploaded.
    db_directory = os.listdir('data/current')
    current_dbfile = str(filename)
    current_dbfile = current_dbfile.replace(".csv", "")
    dbfile = 'sqlite:///'+ current_dbfile + '.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = dbfile
    
    # Copy of the filename used for naming the database. current_dbfile not used because it creates errors.
    database = current_dbfile

    engine = create_engine(dbfile)

    inspector = inspect(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create a dataframe from the csv using pandas
    x = pd.read_csv('data/current/' + filename)
    # Create a database from this dataframe
    x.to_sql(database,  con = engine,  if_exists = "replace", chunksize = 1000)


    column_selected = ""
    inspector = inspect(engine)

    for table_name in inspector.get_table_names():
        tablelist.append(table_name)
    #Create lists of all the colums in the table and the data type for the data display
    for column in inspector.get_columns(table_name):
        columnnamelist.append(column['name'])
        columntypelist.append(column['type'])
    # Identify if any column names have  sql keywords or symbols in them.
    for columnname in columnnamelist:
            for word in sql_keywords:
                if word.lower() == columnname.lower():
                    keywords_in_columns.append([columnname,word])
            for symbol in sql_symbols:
                if symbol in columnname:
                    keywords_in_columns.append([columnname,symbol])
    

    return

def prep(column):
    #This function takes results from  sql queries and makes them more presentable and useable later on in the program
    xx = []
    for x in column:
        x = str(x)
        x = x.replace('(', '')
        x = x.replace(')', '')
        x = x.replace(',', '')
        x = x.replace(']', '')
        x = x.replace('[', '')
        d = x.strip('\'')
        d = x.replace("'", '')
        xx.append(d)
    column = xx
    
    return column


class Col:
    def __init__(self, name, values):
     #Used to store the column name   
        self.name = name
        self.values = values
    #Used to store the column values. 
    def getname(self):
        return self.name

    def setname(self, x):
        self.name = x

    def setvalues(self, x):
        self.values = x

    def getvalues(self):
        return self.values

def generate_where_value(text):
    # This function is serves as a backup solution. It is used in cases where a value is specified but a column name is not. 
    # It looks in the data for that value and also returns the associated column name
        global column_selected
        global columnnamelist
        
        clist = []
        matches = []

        check0, check1, check2 = nounlist(text) #[0]
       
        #If there are no nouns in the  query of the text return 0
        if (len(check2)) == 0:
            return 0

        colnamelist = columnnamelist
        # For each column in the table get each distinct value.
        with engine.connect() as con:
            for x in colnamelist:
                collection = list(con.execute("SELECT DISTINCT " + "\"" + str(x) +"\"" +  "FROM " + database + ";").fetchall())
                collection = prep(collection)
        #Create a Col object that stores the values and the column name
                xcol = Col(str(x),collection)
                clist.append(xcol)
        con.close()

        #Loop throught all the col object created. If a value matches a noun from the query return the value and column name
        for c in clist:
            for x in check2:
                for k in c.getvalues():
                       if x == k or x.lower() == k.lower() or x.replace("'", '') == k:	
                        matches.append([k,c.getname()])	
                        break	
        
        if (len(matches))  == 0:	
            # return "0"	
            str1 = "0 "	
            for k in check2:	
                str1 = str1 + k + ', '	
            str1 = str1+ ';'	
            for k in check0:	
                str1 = str1 + k + ', '	
            return(str1)

        # print("matches = ", matches)
        if (len(matches))  == 0:
            return "0"

        if column_selected == "":
            column_selected = matches[0][1]


        pos = text.find(matches[0][0])    # position of matches[0][0] in string text
        if text.find('not', 0, pos -1 ) > 0:
            op = ' not '
        else:
            op = ' '

        if (len(check2) >= 2): # or len(check0) > 2 
            '''
            str1 = "2 "
            for k in check2:
                str1 = str1 + k + ', '
            str1 = str1+ ';'
            for k in check0:
                str1 = str1 + k + ', '
            return(str1)
            '''
            return "2 where " + op + matches[0][1] + " = " +"'" + matches[0][0] + "' and "
        else:
            return "where " + op + matches[0][1] + " = " +"'" + matches[0][0] + "'"


def numcheck(text):
    #Convert tokens like third,three,3rd into 3
    num = "X"
    # check if the text contains something that can be converted into a number

    NUMmatcher = Matcher(nlp.vocab)
    pattern= [{'ENT_TYPE': 'DATE' }]
    NUMmatcher.add("HelloWorld", None, pattern)


    doc = nlp(text)
    matches = NUMmatcher(doc)
    st = []
    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]
    #Append all tokens that match ENT_DATE to a list
        st.append((str(doc[start:end])))
        span = doc[start:end]
    if (len)(st) > 0:
        x = ' '.join(st)
        reg = first_to_1(x)
        #If token consists of a number and letters like 1st, 2nd, 3rd use regular expression to get only the number element.
        renum = (re.findall(r'[0-9]+',x))
        if len(renum) == 0:
        #if the regular experession fings no digits try first_to_1
            return str(reg)
        num = str(renum[0])
    return num

def first_to_1(text):
    # If the text contains a text ordinal convert it
    t = nltk.word_tokenize(text)
    numbers  = { 'first': 1, 'second':2, 'third' : 3, 'forth': 4, 'fifth': 5, 'sixth': 6, 'seventh':7, 'eighth': 8, 'ninth' : 9, 'tenth' :10}
    for x in t:
        for s in numbers:
            if s == x:
                return(numbers[s])
    return "X"

def proccess_text(text):
    #Convert the text entered to lowercase so case differences are not a problem and then remove any punctuation entered that may interfere with our query.
    text = text.lower()
    #text = text.replace(' id ',' ID ')
    text = text.replace('?', ' ')
    text = text.replace('!', ' ')
    
    last = len(text)-1
    if text[last] == ".":
        text = text[:-1:]


  #Convert text to lemmas to deal with plurals
    plural = WordNetLemmatizer()
    text= nltk.word_tokenize(text)
    string = []
    for x in text:
        s = plural.lemmatize(x)
        string.append(s)
    text = ' '.join(string)
 # Remove possesive 's
    text = text.replace(" 's '",'')
    text = text.replace("'S", "")
    return text

@app.route('/help')
# User information
def help():
    text = 'Enter help text/information here '
    return render_template('help.html', text = text)


@app.route('/', methods=['GET', 'POST'])
def index():
        
    return render_template('index.html')


#
#  Adapted from https://stackoverflow.com/questions/51972481/how-to-open-file-in-browser-using-flask

@app.route('/open', methods=['GET', 'POST'])
def openpdf():
    # Display the user manual from the resources folder    
    return send_from_directory(directory='resources',
                           filename='UserManual.pdf',
                           mimetype='application/pdf')




@app.route('/csv', methods=['GET', 'POST'])

def csvupload():
    #User uploads csv file here
    global upload_status
    if upload_status == False:
        #Display prompt if user has not entered a file.
        message = 'You have not uploaded a database. Please do so below.'
    else:
            message = 'You have current database'
    if request.method == 'POST':
        csv_file = request.files['file']
        if csv_file.filename != '':
            # Use werkzeug.utils to ensure secure filename.
            csv_filename = secure_filename(csv_file.filename)
            csv_file.save(os.path.join(app.config["UPLOAD"],csv_filename))

            #Since the user has now entered a file they can now acces search.html and show_all.html
            upload_status = True
            message = "Succesfully Uploaded "  + csv_file.filename
            database_initialization_sequence(csv_file.filename)

    return render_template('csv.html', m = message)


@app.route('/return-files/')
def return_files_tut():

    return send_file(result_filename, attachment_filename=result_filename, cache_timeout = 0, mimetype = '.csv', as_attachment = 'True')


@app.route('/search')
def search():
    #Prevent the user from searching if nothing is uploaded.
    if upload_status == False:
        return redirect('http://localhost:5000/csv')
    else:
        simplier_terms = []
        #Convert sql types into more understandable lanaguge for users with less programming expereince.
        for x in columntypelist:
            if x == "BIGINT":
                simplier_terms.append("Number")
            elif x == "TEXT":
                simplier_terms.append("Text")
            elif x == "INTEGER":
                simplier_terms.append("Number")
            elif x == "VARCHAR":
                simplier_terms.append("Text")
            elif x =="FLOAT":
                simplier_terms.append("Decimal Point Number")
            else:
                simplier_terms.append(x)

            with engine.connect() as con:
                single_column = str(con.execute("SELECT * FROM " + database + " LIMIT 1;").fetchall())
                single_column = single_column.split(", ")
                single_column = prep(single_column)

            con.close()
        return render_template('search.html', tables = tablelist, columns= columnnamelist, types = simplier_terms, sql = single_column, keyword_guide = keywords_in_columns)





	
@app.route('/query_data', methods=['GET', 'POST'])	

def query_data():	
    	
    nlp = spacy.load("en_core_web_sm")	
    if request.method == 'POST':	
        req = request.form	
        #Get the text entered
        entered_text = req.get("board")
        show_original_text = entered_text
        entered_text = " ".join(entered_text.split())
        #Transform the text in a way that will prevent query errors. 
        entered_text = proccess_text(entered_text)

        nlp = spacy.load("en_core_web_sm")
        #Match column names in query to thoose in the dataset.
        entered_text = substring_and_exact_name_matcing(columnnamelist,entered_text)
        
        
        sqlselect = generate_select(entered_text)
        
        	
        text = sqlselect	
        	
        text = text.replace("AVG", " ")	
        text = text.split()	
        #Generate select, from and where statements andd join them together
        sqlfrom = generate_from(entered_text)	
        sqlwhere = generate_where(entered_text)	
        limit = generate_limit(entered_text)	
        sql = sqlselect + sqlfrom + sqlwhere	
        if limit  != 0:	
            sql = sql + limit
        #If we can not find a pattern with a where statement try to just execute the select from statements	
        if "No Pattern" in sql:	
            sql = sqlselect + sqlfrom	
            #If the text entered matches no pattern we have outlined then return this.
            if "No Pattern" in sql:	
                results = ["No Pattern"]	
                return render_template('query_data.html', text = entered_text,  results =results, s = sql, t = text)	
    if debugMode == False:	
        from datetime import datetime	
        with engine.connect() as con:	
            try:	
            # Excute the sql query we have generated
                results = con.execute(sql).fetchall()	
            # Get the column names selected for the csv file name	
                csvheaders = sqlselect.replace("SELECT ", "")	
                csvheaders = csvheaders.split(",")	
                csvheaders[0] = csvheaders[0].strip()	
                if str(csvheaders[0]) == "*":	
                    csvheaders = columnnamelist	
                now = datetime.now() - timedelta(hours = 1)	
                currenttime = now.strftime("%H:%M")	
                	
                global result_filename	
                headers_for_filename = '_'.join(csvheaders)	
                # Filename for when the user tries to download the result of a query
                result_filename = 'result_'+ str(headers_for_filename)+ "_" + currenttime + '.csv'	
## Adapted from https://stackoverflow.com/questions/47107717/sql-query-output-to-csv	
                with open(result_filename, 'w', newline='') as f_handle:	
                    writer = csv.writer(f_handle)	
                    # Add the header/column names	
                    writer.writerow(csvheaders)	
                    for row in results:	
                        writer.writerow(row)	
                flash('Query returned: ' + str(len(results)) + ' results!' , 'success')	
            except (SQLAlchemyError) as e:	
                err = str(e.__dict__['orig'])	
                error = "An Error has occured, please go back and alter your query. Error details: (" + err + ") - For more information, run this query in Debug Mode"	
                select_error = sqlselect.replace('SELECT' , '')
                # If a generated query has a word or symbol that is a sql keyword and has stopped the query from running it will return a syntax error
                if "syntax error" in error:
                    err = err.replace('near "', '')
                    err = err.replace('": syntax error', '')
                    if err in sql_keywords:
                        
                        error = str(err) + " is an sql keyword  so your query could not be run. Please consult the keyword guide on the search page. You may need to change the column names in your dataset" 
                    else:
                #Syntax error that was caused by a keyword not in our list or some other issue
                        error = " There is a syntax error in your query"
                    
                    return render_template('error.html', error = error, sql = sql ,err = err )
                if "not" in error:	
                    error = "You search did not generate a correct select statment. This means that your search may not have a pattern. Please go back and try and reword you query.  - For more information, run this query in Debug Mode"	
                    return render_template('error.html', error = error, sql = sql )	
                #If the user asks for a column that is not in the data this error will be returned
                if "no such column" in error:

                    error = "An Error has occured. You have entered a column that dosen't exist (" + err + ") A list of  columns is contained in the data display located on the search page. Please go there to rewrite your query  - For more information, run this query in Debug Mode"	
                cnl = columnnamelist	
                err= err.replace("no such column:", "" )	
                	
                random_column_index = random.randint(0,len(cnl)-1)	
                suggestion = entered_text.replace(err, " " + cnl[random_column_index])	
                generated = sql		
                generated = sql	
                return render_template('error_col.html', error = error, col = cnl , e= entered_text ,sql = sql, query =entered_text, sug = suggestion, show = show_original_text )	
        con.close()	
        return render_template('query_data.html', text = entered_text,  results =results, s = sql, headers = csvheaders, show = show_original_text)	


@app.route('/data')
def data():
    if upload_status == False:
        return redirect('http://localhost:5000/csv')
    else:
        clist = []
        with engine.connect() as con:
             collection = list(con.execute("SELECT * FROM " + database + ";").fetchall())	
        return render_template('show_all.html', columns = columnnamelist, data = collection, name = database)

def nounlist(query):
    # Identifys the nouns in the query and indetifies if they are a column/table name or other noun
    nounlist = []
    column_name = []
    table_name = []
    noun_name = []

    text = word_tokenize(query)
    y = nltk.pos_tag(text)
    # print("nounlist: y=", y)
    for i in range(len(y)):
        if "NNS" == y[i][1]  or "NN"  == y[i][1] or  "NNP"  == y[i][1]:
            nounlist.append(y[i][0])
        elif y[i][1] == "JJ" and i == len(y) - 1:
            nounlist.append(y[i][0])
    '''
    for x in y:
        #print("nounlist: x[0]=", x[0])
        #print("nounlist: x[1]=", x[1])
        if "NNS" == x[1]  or "NN"  == x[1] or  "NNP"  == x[1]:	
            nounlist.append(x[0])	
        elif x[1] == "JJ":	
            nounlist.append(x[0])
    '''
    for x in nounlist:
        if x == 'ID':
            firstn = 'id'
            if firstn not in column_name:
                column_name.append(firstn)
        else:
            if x in columnnamelist and  x not in column_name:
                column_name.append(x)
            elif x in tablelist:
                if x not in table_name:
                    table_name.append(x)
            else:
                noun_name.append(x)

    return (column_name,table_name,noun_name)


def generate_limit(text):
    #Our project is based off spacy pattern matching. Pattern matching will be explained here but works the same across the project.
    # All pattern matching code has been adapted from herehttps://spacy.io/usage/rule-based-matching
    
    limitmatcher = Matcher(nlp.vocab)
    #Patterns specify the words or collection of words or parts of speech to match. OP tags specify how many times a token can match from not at all to multiple.
    limit_pattern = [{'ORTH': 'top'}, {'POS': 'NUM'}, {'ORTH': 'records', 'OP' : "*"}]
    limit_pattern1 = [{'ORTH': 'first'}, {'POS': 'NUM'}, {'ORTH': 'records', 'OP' : "*"}]
    limit_pattern2 = [{'ORTH': 'last'}, {'ORTH': 'NUM'}, {'ORTH': 'records', 'OP' : "*"}]
    limit_pattern3 = [{'ORTH': 'top'}, {'ORTH': 'NUM'}, {'ORTH': 'percent'}]
    limit_pattern4 = [{'ORTH': 'bottom'}, {'ORTH': 'NUM'}, {'ORTH': 'percent'}]
    limit_pattern5 = [{'ORTH': 'NUM'}, {'ORTH': 'rows'}]
   
    #Add  the patterns to the matcher
    limitmatcher.add("HelloWorld", None, limit_pattern1)
    limitmatcher.add("HelloWorld", None, limit_pattern2)
    limitmatcher.add("HelloWorld", None, limit_pattern)
    limitmatcher.add("HelloWorld", None, limit_pattern3)
    limitmatcher.add("HelloWorld", None, limit_pattern4)
    limitmatcher.add("HelloWorld", None, limit_pattern5)
    
    #Only spacy nlp objects can be matched so we turn the text entered into nlp.
    doc = nlp(text)
    limit_matches = limitmatcher(doc)
    for match_id, start, end in limit_matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end]
    # span contains a collection of text that matches our patterns
    if ((len(limit_matches)) > 0):
    #If there have a match this text and accesed and used to form our sql query
        for token in span:
            if (token.pos_ == "NUM"):
                num = token.text



        return (" LIMIT " + num)

    return 0




def accept_spaces_between_columnname(columns, text):
    new = []
    to_be_removed = []
    text2 = text
    for y in columns: 
    # Converts column_name into column name so it can be matched to the text entered by the user.
        y = stringcase.sentencecase(y) 
        y = y.lower()
         #If a column is named Column_Name it will put two spaces instead of one so remove one space
        y = y.replace("  "," ")
        new.append(y)
    
    
    for  col in new:
      #Find if the whole column name is in the string. If it is replace the index of the words with whole column name.
        index = text.find(col)
        if index != -1:
            to_be_removed.append(col)
            ind = new.index(col)
            text2 = text2.replace(col,columns[ind])
    return (text2,to_be_removed)
    


def substring_match(column_list, text):
    
    triggered_columns = []
    words= []
    # Adapted from SPACY english stopwords. 
    #As small simple words like " of "  may return every column in a dataset we have decided to not let them trigger column names so the user can get more accurate results
    
    stopwords = ['a', 'all', 'also', 'am', 'an','any', 'are', 'as', 'at', 'back', 'be', 'been', 'both', 'but', 'by', 'call', 'can', 'ca', 'did', 'do', 'does', 'done', 'down', 'due', 'else', 'even', 'ever', 'few', 'five', 'for', 'four', 'from', 'full', 'get', 'give', 'go', 'had', 'has', 'have', 'he', 'her', 'here', 'hers', 'him', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'it', 'its', 'keep', 'last', 'less', 'just', 'made', 'make', 'many', 'may', 'me', 'mine', 'more', 'most', 'move', 'much', 'must', 'my', 'next', 'nine', 'no', 'none', 'nor', 'not', 'now', 'of', 'off', 'on', 'once', 'one', 'only', 'onto', 'or', 'our', 'ours', 'out', 'over', 'own', 'part', 'per', 'put', 're', 'same', 'say', 'see', 'seem', 'she', 'show', 'side', 'six', 'so', 'some', 'such', 'take', 'ten', 'than', 'that', 'the', 'them', 'then', 'they', 'this', 'thru', 'thus', 'to', 'too', 'top', 'two', 'up', 'upon', 'us', 'used', 'very', 'very', 'via', 'was', 'we', 'well', 'what', 'when', 'who', 'whom', 'why', 'will', 'with', 'yet', 'you', 'your']
    if type(text) != list:
        text = text.split()
    
    for w in range(0,len(text)):
        #collection the columns triggered
        triggered_column = []
        word_index = []
        for c in range(0,len(column_list)):
        
            #If we find  a word in the text in the column name we get the whole column and index of the word.
            if column_list[c].find(str(text[w])) != -1:
                
                    
                if column_list[c] not in triggered_column and text[w] not in stopwords:
            
                    triggered_column.append(column_list[c])
               
                    
                    if w not in word_index:
                        word_index.append(text.index(text[w]))
        if len(triggered_column) >= 1:
            triggered_columns.append(triggered_column)
            words.append(word_index)
                              
    return (triggered_columns, words)







def substring_and_exact_name_matcing(columns, text):
    end = accept_spaces_between_columnname(columns,text)
    end_text = end[0]
    end_text2 = end_text
   
    # Making the results from the previous function useable. 
    result = substring_match(columns, end_text)
    new = []
    for x in result[0]:
        # If a word match serveral columns join them together as one string
        newx = ' '.join(x)
        new.append(newx)
        
    #Cobine all word indexs into on string
    nl = []
    for x in result[1]:
        nl = nl + x
    
    end_text2 = end_text2.split()
   
    for w in range(0, len(new)):
        #replace the word that triggered the column name with the column name.
        num  = nl[w]
        end_text2[num] = new[w]
    
    #Sometimes two words next to eachother will trigger the same column name and result in queries with duplicated column names that will not work 
    for x, y in zip(end_text2, end_text2[1:]):
        if x == y:
            end_text2.remove(y)
        elif y in x:
             end_text2.remove(y)
        elif x in y:
            end_text2.remove(x)
             
    
            
        
    end_text2= ' '.join(end_text2) 
    return end_text2

def generate_select (text):
    

    # print('generate_select： text=', text)
    matched = 1
    global column_selected

    nlp = spacy.load("en_core_web_sm")
    Selected = " "
    Select = " "
    Countmatcher = Matcher(nlp.vocab)
    count_pattern = [{'ORTH': 'how'}, {'ORTH': 'many'}]
    count_pattern1 = [{'ORTH': 'overall'}, {'ORTH': 'number'}]
    count_pattern2 = [{'ORTH': 'total'}, {'ORTH': 'number'}]
    Countmatcher.add("HelloWorld", None, count_pattern1)
    Countmatcher.add("HelloWorld", None, count_pattern2)
    Countmatcher.add("HelloWorld", None, count_pattern)
  
   # Average Pronoun/Noun
    Avmatcher = Matcher(nlp.vocab)
    avpattern1 = [{'ORTH': 'average'},
    {'POS': 'NOUN', 'OP': '?'},
    {'POS': 'PROPN', 'OP': '?'}]

    # Avg Pronoun/Noun
    avpattern2 = [{'ORTH': 'avg'},
        {'POS': 'NOUN', 'OP': '?'},
        {'POS': 'PROPN', 'OP': '?'}]
    
    # Average Noun/Pronoun's of Noun by Noun
    avpattern3 = [{'ORTH': 'average'},
                  {'POS': 'NOUN', 'OP': '?'},
                  {'POS': 'PROPN', 'OP': '?'},
                  {'ORTH': "'s", 'OP': '?'},
                  {'POS': 'ADP', 'OP': '?'},
                  {'POS': 'NOUN', 'OP': '?'},
                  {'ORTH': 'by'},
                  {'POS': 'NOUN'}]

    Avmatcher.add("HelloWorld", None, avpattern1)
    Avmatcher.add("HelloWorld", None, avpattern2)
    Avmatcher.add("HelloWorld", None, avpattern3)

    summatcher = Matcher(nlp.vocab)
    # sum of the Noun
    sumpattern = [{'ORTH': 'sum'},
            {'ORTH': 'of'},
           {'ORTH': 'the', 'OP': '?'},
           {'POS': 'NOUN'},
           {'POS': 'NOUN'},
            {'POS' : 'NOUN'}]
    # sum of the Pronoun
    sumpattern1 = [{'ORTH': 'sum'}, {'ORTH' : 'of'},{'ORTH': 'the', 'OP': '?'}, {'POS' : 'PROPN'}]
    # sum of the Noun
    sumpattern2 = [{'ORTH': 'sum'}, {'ORTH' : 'of'},{'ORTH': 'the', 'OP': '?'}, {'POS' : 'NOUN'}]
    

    summatcher.add("HelloWorld", None, sumpattern)
    summatcher.add("HelloWorld", None, sumpattern1)
    summatcher.add("HelloWorld", None, sumpattern2)

    SelectMatcher = Matcher(nlp.vocab)
    # What are the Noun(*) followed by Pronoun(*)
    sel_pattern0 = [{'ORTH' : 'what'},
                    {'ORTH' : 'are'},
                    {'ORTH' : 'the'},
                    {'POS' : 'NOUN', 'OP' : '*'},
                    {'POS' : 'PROPN', 'OP': '*'}]
    # What are the Adjective(*) followed by Pronoun(*)
    sel_pattern0C = [{'ORTH' : 'what'},
                    {'ORTH' : 'are'},
                    {'ORTH' : 'the'},
                    {'POS' : 'ADJ', 'OP' : '*'},
                    {'POS' : 'PROPN', 'OP': '*'}]
    # What are the Noun(*) followed by Adjective(*)
    sel_pattern0D = [{'ORTH' : 'what'},
                    {'ORTH' : 'are'},
                    {'ORTH' : 'the'},
                    {'POS' : 'NOUN', 'OP' : '*'},
                    {'POS' : 'ADJ', 'OP': '*'}]
    # What are the Pronoun(*) followed by Adjective(*)
    sel_pattern0E = [{'ORTH' : 'what'},
                    {'ORTH' : 'are'},
                    {'ORTH' : 'the'},
                    {'POS' : 'PROPN', 'OP' : '*'},
                    {'POS' : 'ADJ', 'OP': '*'}]
    # What are the Adjective(*) followed by Noun(*)
    sel_pattern0F = [{'ORTH' : 'what'},
                    {'ORTH' : 'are'},
                    {'ORTH' : 'the'},
                    {'POS' : 'ADJ', 'OP' : '*'},
                    {'POS' : 'NOUN', 'OP': '*'}]
    #What are the noun(*) followed by Pronoun(*)
    sel_pattern0B = [{'ORTH' : 'what'},
                    {'ORTH' : 'are'},
                    {'ORTH' : 'the'},
                    {'POS' : 'PROPN', 'OP' : '*'},
                    {'POS' : 'NOUN', 'OP': '*'}]
    # What is the Noun(*)
    sel_pattern1 = [{'ORTH' : 'what'},
                    {'ORTH' : 'is'},
                    {'ORTH' : 'the'},
                    {'POS' : 'NOUN', 'OP' : '*'},
                    {'POS' : 'PROPN', 'OP': '*'}]
    # Who is the Noun follwed by Pronoun
    sel_pattern2 = [{'ORTH' : 'who'}, {'ORTH' : 'is'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    # what are the noun followed by pronoun
    sel_pattern3 = [{'ORTH' : 'who'}, {'ORTH' : 'are'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    # what noun
    sel_pattern4 = [{'ORTH' : 'what'}, {'POS' : 'NOUN', 'OP' : '*'}]
    #what are the noun  and nouin
    sel_pattern5 = [{'ORTH' : 'what'}, {'ORTH' : 'are'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'NOUN', 'OP' : '*'}]
    #what are the noun and pronoun
    sel_pattern6 = [{'ORTH' : 'what'}, {'ORTH' : 'are'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'PROPN', 'OP' : '*'}]
    #what are the pronoun and noun
    sel_pattern7 = [{'ORTH' : 'what'}, {'ORTH' : 'are'}, {'ORTH' : 'the'},{'POS' : 'PROPN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'NOUN', 'OP' : '*'}]
    # what ios the noun and noun
    sel_pattern8 = [{'ORTH' : 'what'}, {'ORTH' : 'is'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'NOUN', 'OP' : '*'}]
    # Return text
    sel_pattern9 = [{'ORTH' : 'return'}, {'IS_ASCII': True} ]
    # Return Verb
    sel_pattern10 = [{'ORTH' : 'return'}, {'POS' : 'VERB'} ]
    # Return the Noun followed by Pronoun
    sel_pattern11 = [{'ORTH' : 'return'},{'ORTH' : 'the'}, {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    # show the Noun followed by Pronoun
    sel_pattern12 = [{'ORTH' : 'show'},{'ORTH' : 'the'}, {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    # Select the noun followed by Pronoun
    sel_pattern13 = [{'ORTH' : 'select'},{'ORTH' : 'the'}, {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    #display the noun followed by Pronoun
    sel_pattern14 = [{'ORTH' : 'display'},{'ORTH' : 'the'}, {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    #what is the noun and noun
    sel_pattern15 = [{'ORTH' : 'what'}, {'ORTH' : 'is'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'NOUN', 'OP' : '*'}]
    # what is the noun and the pronoun
    sel_pattern16 = [{'ORTH' : 'what'}, {'ORTH' : 'is'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'PROPN', 'OP' : '*'}]
    # What is the Noun and Propernoun
    sel_pattern17 = [{'ORTH' : 'what'}, {'ORTH' : 'is'}, {'ORTH' : 'the'},{'POS' : 'PROPN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'NOUN', 'OP' : '*'}]
    # What is the Propernoun and Noun
    sel_pattern18 = [{'ORTH' : 'what'}, {'ORTH' : 'is'}, {'ORTH' : 'the'},{'POS' : 'NOUN', 'OP' : '*'}, {'ORTH': ',', 'OP': '?'}, {'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : 'and'}, {'POS' : 'NOUN', 'OP' : '*'}]
    # What are the Noun , Noun and
    sel_pattern19 = [{'ORTH' : 'what'}, {'ORTH' : 'are'}, {'ORTH': 'the'}, {'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : ',', 'OP': '?'}, {'POS' : 'NOUN', 'OP': '*'}, {'ORTH' : 'and', 'OP': '*'}, {'POS' : 'NOUN', 'OP': '*'}]
    # Verb the Noun , Noun and Noun
    sel_pattern24 = [{'POS': 'VERB'}, {'ORTH': 'the'}, {'POS' : 'NOUN', 'OP' : '*'}, {'ORTH' : ',', 'OP': '?'}, {'POS' : 'NOUN', 'OP': '*'}, {'ORTH' : 'and', 'OP': '*'}, {'POS' : 'NOUN', 'OP': '*'}]
    sel_pattern25 = [{'ORTH' : 'what'} ,{'POS':'AUX'} ,{'POS':'DET'} ,{'POS':'NOUN'} ,{'ORTH':'and', 'OP': '?'} ,{'POS': 'PROPN'} ]
    
    SelectMatcher.add("HelloWorld", None, sel_pattern25)
    SelectMatcher.add("HelloWorld", None, sel_pattern0)
    SelectMatcher.add("HelloWorld", None, sel_pattern1)
    SelectMatcher.add("HelloWorld", None, sel_pattern2)
    SelectMatcher.add("HelloWorld", None, sel_pattern3)
    SelectMatcher.add("HelloWorld", None, sel_pattern4)
    SelectMatcher.add("HelloWorld", None, sel_pattern5)
    SelectMatcher.add("HelloWorld", None, sel_pattern6)
    SelectMatcher.add("HelloWorld", None, sel_pattern7)
    SelectMatcher.add("HelloWorld", None, sel_pattern8)
    SelectMatcher.add("HelloWorld", None, sel_pattern9)
    SelectMatcher.add("HelloWorld", None, sel_pattern10)
    SelectMatcher.add("HelloWorld", None, sel_pattern11)
    SelectMatcher.add("HelloWorld", None, sel_pattern12)
    SelectMatcher.add("HelloWorld", None, sel_pattern13)
    SelectMatcher.add("HelloWorld", None, sel_pattern14)
    SelectMatcher.add("HelloWorld", None, sel_pattern0B)
    SelectMatcher.add("HelloWorld", None, sel_pattern0C)
    SelectMatcher.add("HelloWorld", None, sel_pattern0D)
    SelectMatcher.add("HelloWorld", None, sel_pattern0E)
    SelectMatcher.add("HelloWorld", None, sel_pattern0F)
    SelectMatcher.add("HelloWorld", None, sel_pattern15)
    SelectMatcher.add("HelloWorld", None, sel_pattern16)
    SelectMatcher.add("HelloWorld", None, sel_pattern17)
    SelectMatcher.add("HelloWorld", None, sel_pattern18)
    SelectMatcher.add("HelloWorld", None, sel_pattern19)
    SelectMatcher.add("HelloWorld", None, sel_pattern24)
    
    
    
   

    # All details(?)
    AllMatcher = Matcher(nlp.vocab)
    all_pattern1 = [{'ORTH' : 'All'}, {'ORTH' : 'details' , 'OP': '?'}]
    all_pattern2 = [{'ORTH' : 'all'}, {'ORTH' : 'details' , 'OP': '?'}]

    AllMatcher.add("HelloWorld", None, all_pattern1)
    AllMatcher.add("HelloWorld", None, all_pattern2)

    # Which Noun
    Whichmatcher = Matcher(nlp.vocab)
    which_pattern = [{'ORTH': 'which'}, {'POS': 'NOUN'}]
    Whichmatcher.add("HelloWorld", None, which_pattern)

    #Show/Display me(?)/the(?) Number
    ShowMatcher = Matcher(nlp.vocab)
    Show_pattern1 = [{'ORTH' : 'show'}, {'ORTH' : 'me' , 'OP': '?'}, {'POS': 'NUM', 'OP': '?'}]
    Show_pattern2 = [{'ORTH' : 'display'}, {'ORTH' : 'me' , 'OP': '?'}, {'POS': 'NUM', 'OP': '?'}]
    Show_pattern3 = [{'ORTH' : 'show'}, {'ORTH' : 'the' , 'OP': '?'}, {'POS': 'NUM', 'OP': '?'}]
    Show_pattern4 = [{'ORTH' : 'display'}, {'ORTH' : 'the' , 'OP': '?'}, {'POS': 'NUM', 'OP': '?'}]
    ShowMatcher.add("HelloWorld", None, Show_pattern1)
    ShowMatcher.add("HelloWorld", None, Show_pattern2)
    ShowMatcher.add("HelloWorld", None, Show_pattern3)
    ShowMatcher.add("HelloWorld", None, Show_pattern4)
    

    doc = nlp(text)
    count_matches = Countmatcher(doc)
    for match_id, start, end in count_matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end]
    if ((len(count_matches)) > 0):
        matched = 0
        Selected = "COUNT(*) "
        Select = "SELECT  " + Selected
        return(Select)
 #Checking   if  the entered text matches our patterns that trigger the  word  which to be used.
    which_matches = Whichmatcher(doc)
    for match_id, start, end in which_matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end]
    if ((len(which_matches)) > 0):
        matched = 0
        Selected = " * "
        for token in span:
            if (token.pos_ == "NOUN"):
                if token.text in columnnamelist:
                    Selected = token.text

        column_selected = Selected
        # print("Selected = ", Selected)
        Select = "SELECT  " + Selected
        return(Select)
    #Checking   if  the entered text matches our patterns that trigger the keyword AVG to be used.
    avmatches = Avmatcher(doc)
    for match_id, start, end in avmatches:
            string_id = nlp.vocab.strings[match_id]  # Get string representation
            span = doc[start:end]
    if ((len(avmatches)) > 0):
        matched = 0
        W = " "
        G = ""
        by = 0

        for token in span:
            if token.text == "by":
                by = 1
            if (by == 0 and (token.pos_ == "NOUN" or token.pos_ == "PROPN")):	
                W = token.text	
            if (by == 1 and (token.pos_ == "NOUN" or token.pos_ == "PROPN")):	
                G = token.text


        if by == 0:
            Selected = "AVG(" + W +")"
        else:
            Selected = G + ", AVG(" + W +")"

        Select = "SELECT  " + Selected
        return(Select)
    #Checking   if  the entered text matches our patterns that trigger the keyword SUM  to be used.
    summatches = summatcher(doc)
    for match_id, start, end in summatches:
            string_id = nlp.vocab.strings[match_id]  # Get string representation
            span = doc[start:end]
    if (len(summatches)) > 0:
        matched = 0
        W = " "
        for token in span:
            if token.pos_ == "NOUN"  and  token.text != 'sum' or token.pos_ == "PROPN" and  token.text != 'sum':
                W = token.text


        if W in columnnamelist:
            Selected = "SUM(" + W +")"
        else:
            # Sometimes people may use the word sum when they want the count returned. If there are no columns provided we return the count instead.
            Selected ="COUNT(*)"

        Select = "SELECT  " + Selected
        return(Select)


    # Select columns for general queries that do not use any other keyword
    Selectmatches = SelectMatcher(doc)
    for match_id, start, end in Selectmatches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        spanx = doc[start:end]
#        print("generate_select: spanx = ", spanx)

    if (len(Selectmatches)) > 0:
            to_text = []
            matched = 0
            set1 = []
            
            for token in spanx:
                if token.text in columnnamelist:
                        set1.append(token.text)
           #Even if a noun or propn is not a column name we want to add it to the generated query so we can present the error to the user.
            if len(set1) == 0:	
                for token in spanx:	
                    if token.pos_ == "NOUN" or token.pos_ == "PROPN":	
                        set1.append(token.text)	
            my_string = ','.join(set1)	
            
            Selected = my_string	
            column_selected = my_string	
            # print("column_selected = ", column_selected)	

#            print("column_selected = ", column_selected)
 # #Checking   if  the entered text matches our patterns that trigger the keyword all aka *  to be used.
    AllMatches = AllMatcher(doc)
    for match_id, start, end in AllMatches:
            string_id = nlp.vocab.strings[match_id]  # Get string representation
            span = doc[start:end]
    if (len(AllMatches)) > 0:
        matched = 0
        Selected = "*"

    # If any patterns with the word show match the entered text
    doc = nlp(text)
    show_matches = ShowMatcher(doc)
    for match_id, start, end in show_matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end]
        
    if ((len(show_matches)) > 0):
        matched = 0
        Selected = "* "
        Select = "SELECT  " + Selected
        return(Select)
    
    
    # If we are not looking for the count then look for the columns aka nouns in the query.
    if matched != 0:
        mylist = []
        li = nounlist(text)[0]

        my_string = ','.join(li)

        Selected = Selected + my_string
        if (len(mylist)) == 0:
            # If there are no nouns or column names in a query
            Selected = "You have not enteed a correct select statment"

    Select = "SELECT  " + Selected
    return(Select)


def generate_from ( text ):
    # If I have extra time I will get the table names like I got the column names and then we can say this is generated and not hard coded.
    where = " where "
    Froms = " "
    From =  " FROM " +  database + " "

    return From

def generate_where( text ):
 
   
    

    #List of words that detemine the operator we use.
    less_than_words = ['below' , 'less', 'fewer', 'lower', 'before', 'smaller', 'shorter', 'under', 'beneath']
    greater_than_words = ['greater', 'more', 'higher', 'above', 'after', 'bigger', 'surpasing','suprasses','exceeds' 'exceeding', 'longer', 'beyond']
    equals_words = ['is', 'equals' , 'having','are','in','receiving','getting']
    min_words = ['least', 'minumum','min' 'fewest', 'worst','last','lowest', 'last', 'shortest', 'bottom']
    max_words = ['best', 'most', 'highest', 'maxiumum', 'max', 'winner', 'first', 'longest' 'peak', 'top']


   
    text1 = str(generate_where_value(text))

    global column_selected
    match = 0
    gen_where = " where "

    if text1[0] == 'w':
        return(text1)

    if text1[0] == '2':
        gen_where = text1[2:]
        match = 2
    '''   	
    else:	
        match = 0	
        gen_where = text1	
    return(gen_where)	
    '''	
    


    nlp = spacy.load("en_core_web_sm")

    # where contains multi conditions
    multipattern1 = [{'POS': 'PRON', 'OP': '?'},
                     {'POS': 'AUX', 'OP': '?'},
                     {'ORTH': 'not', 'OP': '?'},
                     {'POS': 'ADP'},
                     {'POS': 'NOUN'},
                     {'POS': 'NUM'}]

    Multi1_matcher = Matcher(nlp.vocab)
    Multi1_matcher.add("HelloWorld", None, multipattern1)

    # with(ADP) GPA(PROPN) greater(ADJ) than(SCONJ) 2(NUM) from(ADP) year(NOUN) 1(NUM)
    multipattern2 = [{'POS': 'ADP'},
                     {'POS': 'PROPN'},
                     {'POS': 'AUX', 'OP': '?'},
                     {'POS': 'ADJ'},
                     {'POS': 'SCONJ'},
                     {'POS': 'NUM'},
                     {'POS': 'ADP'},
                     {'POS': 'NOUN'},
                     {'POS': 'AUX', 'OP': '?'},
                     {'POS': 'NUM'}]

    Multi2_matcher = Matcher(nlp.vocab)
    Multi2_matcher.add("HelloWorld", None, multipattern2)

    # WHERE  YEAR(noun) IS(aux) 3(num)
    pattern1 = [{'POS': 'NOUN'},
                {'POS': 'AUX'},
                {'ORTH': 'not', 'OP': '?'},
                {'POS': 'NUM'}]
    # WHERE  GPA(pronoun) IS(aux) 3(num)
    pattern2= [{'POS': 'PROPN'},
                {'POS': 'AUX'},
                {'ORTH': 'not', 'OP': '?'},
                {'POS': 'NUM'}]
     # who are female	
    pattern89= [{'POS': 'NOUN'},	
                {'POS': 'AUX'},	
                {'ORTH': 'not', 'OP': '?'},	
                {'POS': 'NOUN'}]	
    # who are female	
    pattern91= [{'POS': 'NOUN'},	
                {'POS': 'AUX'},	
                {'ORTH': 'not', 'OP': '?'},	
                {'POS': 'ADJ'}]	
    


    # WHERE  year(noun) IS(aux) greater(adj) than(sconj) 3(num)
    pattern3= [{'POS': 'NOUN'},
               {'POS': 'AUX'},
               {'ORTH': 'not', 'OP': '?'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]
    # # WHERE  GPA(pronoun) IS(aux) greater(adj) than(sconj) 3(num)
    pattern4= [{'POS': 'PROPN'},
               {'POS': 'AUX'},
               {'ORTH': 'not', 'OP': '?'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]
    pattern24= [{'POS': 'DET'},
               {'POS': 'AUX'},
               {'ORTH': 'not', 'OP': '?'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]


    # # WHERE  GPA(pronoun) greater(adj) than(sconj) 3(num)
    pattern14= [{'POS': 'PROPN'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]

    # WHERE   a(det) higher(ADJ) GPA(PROPN) than(SCONJ) 2(NUM)
    pattern15= [{'POS':'DET'},
                {'POS':'ADJ'},
                {'POS':'PROPN'},
                {'POS':'SCONJ'},
                {'POS':'NUM'}]

    pattern12= [{'POS': 'ADJ', 'OP': '?'},
                {'POS': 'ADJ' },
                {'POS' : 'NOUN'}]

    # WHERE not in(ADP) the(DET) third(ADJ) year(NOUN)
    pattern13= [{'ORTH': 'not', 'OP': '?'},
               {'POS': 'ADP'},
               {'POS': 'DET'},
               {'POS': 'ADJ'},
               {'POS': 'NOUN'}]

    # WHERE not in(ADP) the(DET) third(ADJ) year(NOUN)
    pattern113= [{'POS': 'CCONJ'},
                {'POS': 'AUX'},
               {'POS': 'ADP'},
               {'POS': 'DET'},
               {'POS': 'ADJ'},
               {'POS': 'NOUN'}]

    pattern34= [{'POS': 'DET'},
               {'POS': 'ADJ'},
               {'POS': 'SCONJ'},
               {'POS': 'NUM'}]


    # YEAR(noun) is(aux) below(adp) num
    pattern5 =[{'POS': 'NOUN'},
               {'POS': 'AUX'},
               {'ORTH': 'not', 'OP': '?'},
               {'POS': 'ADP'},
               {'POS': 'NUM'}]

    # GPA(pronoun) is(aux) below(adp) num
    pattern6 =[{'POS': 'PROPN'},
                   {'POS': 'AUX'},
                   {'ORTH': 'not', 'OP': '?'},
                   {'POS': 'ADP'},
                   {'POS': 'NUM'}]

    # GPA(pronoun) below(adp) num
    pattern16 =[{'POS': 'PROPN'},
                   {'POS': 'ADP'},
                   {'POS': 'NUM'}]

    # Year (noun) equals (aux) 3(num)
    pattern7 =[
               {'POS': 'PROPN'},
               {'POS': 'VERB', 'TAG': 'VBZ'},
               {'POS': 'NUM'}]
    # Year (noun) equals (aux) 3(num)
    pattern8 =[
               {'POS': 'NOUN'},
               {'POS': 'VERB', 'TAG': 'VBZ'},
               {'POS': 'NUM'}]
    # Department(noun) equals (aux) English(noun)
    pattern31 =[{'POS': 'PROPN'},
                {'POS': 'VERB', 'TAG': 'VBZ'},
                {'POS': 'NOUN'}]
    # Department(noun) equals (aux) English(noun)
    pattern32 =[{'POS': 'NOUN'},
                {'POS': 'VERB', 'TAG': 'VBZ'},
                {'POS': 'NOUN'}]

    pattern9= [{'POS': 'VERB' }, {'POS' : 'PROPN'}, {'POS' : 'ADP'}, {'POS' : 'NUM'}]

    pattern10= [{'POS': 'VERB' }, {'POS' : 'NOUN'}, {'POS' : 'ADP'}, {'POS' : 'NUM'}]

    # Year (noun) is(AUX) equal(ADJ) to(ADP) 3(num)
    pattern11= [{'POS': 'NOUN' },
                {'POS': 'AUX', 'OP': '?'},
                {'POS': 'ADJ'},
                {'POS': 'ADP', 'OP': '?'},
                {'POS': 'NUM'}]

    # with(ADP) a(DET) GPA(PROPN) that(DET) is(AUX) not(PART) 4(NUM)
    pattern20 =[{'POS': 'ADP'},
               {'POS': 'DET'},
               {'POS': 'PROPN'},
               {'POS': 'DET'},
               {'POS': 'AUX'},
               {'ORTH': 'not', 'OP': '?'},
               {'POS': 'NUM'}]
    # are not in year 3
    pattern21 =[{'POS': 'AUX', 'OP': '?'},
               {'ORTH': 'not', 'OP': '?'},
               {'POS': 'ADP'},
               {'POS': 'NOUN'},
               {'POS': 'NUM'}]

    # students(NOUN) who(PRON) live (VERB) in(ADP) Australia(PROPN)
    pattern22 =[{'POS': 'NOUN'},
                {'POS': 'PRON'},
               {'POS': 'VERB'},
               {'POS': 'ADP'},
               {'POS': 'PROPN'}]

 # students from the year 2010
    pattern23 =[{'POS': 'NOUN'},
                {'ORTH':'from'},
                {'ORTH':'the'},
                {'POS':'NOUN'},
                {'POS':'NUM'}]
    # students from 2009
    pattern24 =[{'POS':'NOUN'},
                {'ORTH':'from'},
                {'POS':'NUM'}]
    
    # GPA(pronoun) below(adp) num
    pattern16 =[{'ORTH': 'not', 'OP': '?'},
            {'POS': 'AUX', 'OP': '?'},
            {'POS': 'DET', 'OP': '?'},
            {'POS': 'PROPN'},
            {'POS': 'ADP'},
            {'POS': 'NUM'}]
    # has greater than NUM noun    
    pattern17 = [{ 'POS' : 'ADJ' } ,{ 'POS' : 'SCONJ' } ,{ 'POS' : 'NUM' } ,{ 'POS' : 'PROPN' }]   
    #
    pattern18 = [{ 'POS' : 'NOUN' } ,{'POS' : 'ADJ' } ,{ 'POS' : 'SCONJ' } ,{ 'POS' : 'NUM' }]




    OPmatcher = Matcher(nlp.vocab)
    OPmatcher.add("HelloWorld", None, pattern1)
    OPmatcher.add("HelloWorld", None, pattern2)
    OPmatcher.add("HelloWorld", None, pattern3)
    OPmatcher.add("HelloWorld", None, pattern4)
    OPmatcher.add("HelloWorld", None, pattern5)
    OPmatcher.add("HelloWorld", None, pattern6)
    OPmatcher.add("HelloWorld", None, pattern7)
    OPmatcher.add("HelloWorld", None, pattern8)
    OPmatcher.add("HelloWorld", None, pattern9)
    OPmatcher.add("HelloWorld", None, pattern10)
    OPmatcher.add("HelloWorld", None, pattern11)
    OPmatcher.add("HelloWorld", None, pattern12)
    OPmatcher.add("HelloWorld", None, pattern14)
    OPmatcher.add("HelloWorld", None, pattern16)
    OPmatcher.add("HelloWorld", None, pattern17)
    OPmatcher.add("HelloWorld", None, pattern18)
    OPmatcher.add("HelloWorld", None, pattern24)
    OPmatcher.add("HelloWorld", None, pattern34)
    OPmatcher.add("HelloWorld", None, pattern13)
    OPmatcher.add("HelloWorld", None, pattern113)
    OPmatcher.add("HelloWorld", None, pattern15)
    OPmatcher.add("HelloWorld", None, pattern20)
    OPmatcher.add("HelloWorld", None, pattern21)
    OPmatcher.add("HelloWorld", None, pattern22)
    OPmatcher.add("HelloWorld", None, pattern31)
    OPmatcher.add("HelloWorld", None, pattern32)
    OPmatcher.add("HelloWorld", None, pattern89)
    OPmatcher.add("HelloWorld", None, pattern91)
    OPmatcher.add("HelloWorld", None, pattern23)
    OPmatcher.add("HelloWorld", None, pattern24)
    


    Extramatcher = Matcher(nlp.vocab)
    Expattern1 = [{'POS': 'ADJ'}, {'POS': 'ADJ' }, {'POS' : 'NOUN'}]
    Expattern2 = [{'ORTH': 'by'}, {'POS' : 'NOUN'}]
    Expattern3 = [{'POS': 'DET'}, {'POS' : 'ADJ'}, {'POS': 'PROPN'}, {'ORTH': 'combined'}]
    Extramatcher.add("HelloWorld", None, Expattern1)
    Extramatcher.add("HelloWorld", None, Expattern2)
    Extramatcher.add("HelloWorld", None, Expattern3)


    B= Matcher(nlp.vocab)
    #Noun between _ and _
    Between = [{'POS' : 'NOUN'},
               {'ORTH': 'between'},
               {'POS': 'NUM',},
               {'POS': 'CCONJ'},
               {'POS': 'NUM'}]
    #Pronoun is(*) Not(*) Between _ and _
    B2 =  [{'POS' : 'PROPN'},
           {'POS': 'AUX', 'OP': '?'},
           {'ORTH': 'not', 'OP': '?'},
           {'ORTH': 'between'},
           {'POS': 'NUM',},
           {'POS': 'CCONJ'},
           {'POS': 'NUM'}]
    #Noun Not(*) Between _ and _ 
    B3 = [{'POS': 'NOUN'},
        {'POS': 'AUX', 'OP': '?'},
        {'ORTH': 'not', 'OP':'?'},
        {'ORTH': 'between'},
          {'POS': 'NUM'},
          {'POS': 'CCONJ'},
          {'POS': 'NUM'}]
   
   # Noun  In the range from _ to _
    B4 = [{'POS': 'NOUN'},
          {'ORTH': 'is'},
          {'ORTH': 'in'},
            {'ORTH': 'the'},
            {'ORTH': 'range'},
            {'ORTH': 'from'},
            {'POS': 'NUM'},
            {'ORTH': 'to'},
            {'POS': 'NUM'}]
    
    #Proper Noun In the range from _ to _
    B5 = [{'POS': 'PROPN'},
          {'ORTH': 'is'},
          {'ORTH': 'in'},
            {'ORTH': 'the'},
            {'ORTH': 'range'},
            {'ORTH': 'from'},
            {'POS': 'NUM'},
            {'ORTH': 'to'},
            {'POS': 'NUM'}]

    B.add("HelloWorld", None, Between)
    B.add("HelloWorld", None, B2)
    B.add("HelloWorld", None, B3)
    B.add("HelloWorld", None, B4)

    Country_Department = Matcher(nlp.vocab)
    CD1 = [{'ORTH' : 'department'},
        {'ORTH': 'is'},
        {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    CD2 = [{'ORTH' : 'country'},
        {'ORTH': 'is'},
        {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    CD3 = [{'POS': 'NOUN'},
        {'ORTH': 'equals'},
        {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    CD4 = [{'POS': 'propn'},
        {'ORTH': 'equals'},
        {'POS' : 'NOUN', 'OP' : '*'}, {'POS' : 'PROPN', 'OP': '*'}]
    CD5 = [ {'ORTH': 'in', 'OP': '?'},
            {'ORTH': 'the', 'OP': '?'},
            {'POS' : 'PROPN'}, {'ORTH' : 'department'}]

    Country_Department.add("HelloWorld", None, CD1)
    Country_Department.add("HelloWorld", None, CD2)
    Country_Department.add("HelloWorld", None, CD3)
    Country_Department.add("HelloWorld", None, CD4)
    # Country_Department.add("HelloWorld", None, CD5)

    LikeMatcher = Matcher(nlp.vocab)
    like1 = [{'POS': 'NOUN'},{'ORTH': 'starting'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like2 = [{'POS': 'NOUN'}, {'ORTH': 'starts'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like3 = [{'POS': 'PROPN'},{'ORTH': 'starting'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like4 = [{'POS': 'PROPN'}, {'ORTH': 'starts'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like5 = [{'POS': 'NOUN'},{'ORTH': 'ending'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like6 = [{'POS': 'NOUN'}, {'ORTH': 'ends'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like7 = [{'POS': 'PROPN'},{'ORTH': 'ending'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like8 = [{'POS': 'PROPN'}, {'ORTH': 'ends'}, {'ORTH': 'with'},{'IS_ASCII': True}]
    like9 = [{'POS': 'NOUN'},{'ORTH': 'containing'},{'IS_ASCII': True}]
    like10 = [{'POS': 'NOUN'}, {'ORTH': 'contains'},{'IS_ASCII': True}]
    like11= [{'POS': 'PROPN'},{'ORTH': 'containing'},{'IS_ASCII': True}]
    like12= [{'POS': 'PROPN'}, {'ORTH': 'contains'},{'IS_ASCII': True}]

    LikeMatcher.add("HelloWorld", None, like1)
    LikeMatcher.add("HelloWorld", None, like3)
    LikeMatcher.add("HelloWorld", None, like3)
    LikeMatcher.add("HelloWorld", None, like4)
    LikeMatcher.add("HelloWorld", None, like5)
    LikeMatcher.add("HelloWorld", None, like6)
    LikeMatcher.add("HelloWorld", None, like7)
    LikeMatcher.add("HelloWorld", None, like8)
    LikeMatcher.add("HelloWorld", None, like9)
    LikeMatcher.add("HelloWorld", None, like10)
    LikeMatcher.add("HelloWorld", None, like11)
    LikeMatcher.add("HelloWorld", None, like12)

    if match == 0:
        doc=nlp(text)
        Multi2_matches = Multi2_matcher(doc)
        maxlen = 0
        span = ""
        for match_id, start, end in Multi2_matches:
            string_id = nlp.vocab.strings[match_id]  # Get string representation
            s1 = str(doc[start:end])
            if ( len(s1.split(" ")) >= maxlen ):
                maxlen = len(s1.split(" "))
                span = doc[start:end]


        if (len(Multi2_matches)>0):
            nums = []
            oper = []
            Wb = []
            nouns = nounlist(text)[0]
            i = 0

            for token in span:
                if token.pos_ == "NUM":
                    nums.append(token.text)
                if token.pos_ == "PROPN" or token.pos_ == "NOUN":
                    Wb.append(token.text)
                    oper.append('=')
                    i = i + 1

                if token.text in greater_than_words:
                    oper[i-1] = '>'
                elif token.text in less_than_words:
                    oper[i-1] = '<'
            if i >0:
                whered = " " + gen_where + Wb[0] + oper[0] + nums[0]
                for j in range(1,i):
                    whered = whered  + " and " + Wb[j] + oper[j] + nums[j]

            return  whered


    if match >0:
        doc=nlp(text)
        Multi1_matches = Multi1_matcher(doc)
        maxlen = 0
        span = ""
        for match_id, start, end in Multi1_matches:
            string_id = nlp.vocab.strings[match_id]  # Get string representation
            s1 = str(doc[start:end])
            if ( len(s1.split(" ")) >= maxlen ):
                maxlen = len(s1.split(" "))
                span = doc[start:end]

        if (len(Multi1_matches)>0):
            nums = []
            oper = []
            Wb = []
            nouns = nounlist(text)[0]
            i = 0

            for token in span:
                if token.pos_ == "NUM":
                    nums.append(token.text)
                if token.pos_ == "PROPN" or token.pos_ == "NOUN":
                    Wb.append(token.text)
                    oper.append('=')
                    i = i + 1
                if token.text in greater_than_words:
                    oper[i-1] = '>'
                elif token.text in less_than_words:
                    oper[i-1] = '<'

            if i >0:
                whered = " " + gen_where + Wb[0] + oper[0] + nums[0]
                for j in range(1,i):
                    whered = whered  + " and " + Wb[j] + oper[j] + nums[j]

            return  whered


    doc = nlp(text)
    likematches = LikeMatcher(doc)
    for match_id, start, end in likematches:
            string_id = nlp.vocab.strings[match_id]  # Get string representation
            span = doc[start:end]
    if ((len(likematches)) > 0):
        matched = 0
        # We cannot search First names begining with A because it things it means the word a not the letter.
        doublemeaningletters = ["I", "A", "An", "Hi", "to", "of", "in", "it", "is", "as", "at", "be", "we", "he", "so", "on", "an", "or", "do", "if", "up", "by","my"]
        nouns = []
        for token in span:
            if (token.pos_ == "NOUN" or token.pos_ == "PROPN" or token.pos_ == "NUM"):
                nouns.append(token.text)
        for token in span:
            if (token.text in doublemeaningletters):
                nouns.append(token.text)
        # nouns[0] is the chosen column name and nouns[1] is the value in thoose columns we are searching for
        for token in span:
            if (token.text == "starting" or  token.text == "starts"):
                return " Where  " + nouns[0] + " like " + "\"" + nouns[1] +"%\""
            elif (token.text == "ends" or  token.text == "ending"):
                return " Where  " + nouns[0] + " like " + "\"%" + nouns[1] +"\""
            elif (token.text == "contains" or  token.text == "containing"):
                return " Where  " + nouns[0] + " like " + "\"%" + nouns[1] +"%\""




    doc = nlp(text)
    Betmatches = B(doc)
    maxlen = 0
    for match_id, start, end in Betmatches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        s1 = str(doc[start:end])
        if ( len(s1.split(" ")) >= maxlen ):
            maxlen = len(s1.split(" "))
            span = doc[start:end]
    #if the text entered matches any of our patterns in betmatches we will then generate a sql statment that uses the keyword between
    if ((len(Betmatches)) > 0):
        nums = []
        Wb = []
        nouns = nounlist(text)[0]


        for token in span:
            if token.text == "not":
                where = " where not "
            if token.pos_ == "NUM":
                if numcheck(token.text) != 'X':
                    nums.append(numcheck(token.text))
                nums.append(token.text)
            # The word range is used in our patterns so we do not want to select it as the column we are searching for    
            if token.pos_ == "PROPN" or token.pos_ == "NOUN" and token.pos_ != 'range' :
                Wb = token.text
        return  " " + gen_where +  Wb + " between " + (str(nums[0])) + " and " + (str(nums[1]))



    doc = nlp(text)
    CDmatches = Country_Department(doc)
    for match_id, start, end in CDmatches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end]

    if ((len(CDmatches)) > 0):
        nums = []
        nouns = nounlist(text)[0]

        for token in span:
            if token.pos_ == "NOUN":
                nums.append(token.text)

            if token.pos_ == "PROPN":
                Wb = token.text
        return  " " + gen_where + (str(nums[0]))  + " = " + "'" + Wb + "'"


    doc = nlp(text)
    EX_matches = Extramatcher(doc)
    for match_id, start, end in EX_matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        span = doc[start:end]

    if ((len(EX_matches)) > 0):
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(str(span))

        hl = 0
        W = " "
        avgorsum = 0
        for token in span:
            if token.pos_=='NOUN' or token.pos_=='PROPN':
                W = token.text
            if token.text == 'combined':
                avgorsum = 1
            if token.text == 'by':
                hl = 2
            if token.text in min_words:
                hl = 0
            if token.text in max_words:
                hl = 1
        if avgorsum == 0:
            if hl == 1:
                return(" group by "+ column_selected + " order by " + "avg("+ W +") desc limit 1" ) # column_selected
            elif hl == 0:
                return(" group by "+ column_selected + " order by " + "avg("+ W +") asc limit 1" ) # column_selected
            else:
                return(" group by "+ W)
        else:
            if hl == 1:
                return(" group by "+ column_selected + " order by " + "sum("+ W +") desc limit 1" ) # column_selected
            elif hl == 0:
                return(" group by "+ column_selected + " order by " + "sum("+ W +") asc limit 1" ) # column_selected
            else:
                return(" group by "+ W)


    doc = nlp(text)
    matches = OPmatcher(doc)
    maxlen = 0
    span = ""
    for match_id, start, end in matches:
        string_id = nlp.vocab.strings[match_id]  # Get string representation
        s1 = str(doc[start:end])
        if ( len(s1.split(" ")) >= maxlen ):
            maxlen = len(s1.split(" "))
            span = doc[start:end]

    if ((len(matches)) > 0):
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(str(span))
        W = " "
        num = " "
        for token in doc:
            if token.pos_=='NOUN' or token.pos_=='PROPN':
                W = token.text
            if token.pos_=='DET':
                W = column_selected
            

        doc1 = nlp(str(span))
        o = " "
        where = gen_where
        for token in doc1:
#            print("token.text = ", token.text)
#            print("token.pos_ = ", token.pos_)
            if token.pos_ == "ADP" or  token.pos_ == "ADJ" or token.pos_ == "ADV" or token.pos_ == "VERB":
                o = token.text
            if token.pos_ == "NUM":
                num = token.text
        for token in doc1:
           if num == " " and token.pos_ == 'PROPN':
                num == token.text
               
           if token.text == "not":
                where = " " + gen_where + " not "
        
        
        ordinal = ['','first','second','third','fourth','fifth','sixth','seventh','eighth','nineth','tenth']
        for i in range(len(ordinal)):
            if o == ordinal[i]:
                num = str(i)
#       print("num=",num)
        if num == " ":
            ordinal2 = ['','1st','2nd','3rd','4th','5th','6th','7th','8th','9th','10th']
            for i in range(len(ordinal2)):
                if o == ordinal2[i]:
                    num = str(i)
        ordinal3 = ['','one','two','three','four','five','six','seven','eight','nine','ten']
        for i in range(len(ordinal3)):
            if num == ordinal3[i]:
               num = str(i)

        #Check to see if the phrase 3rd year or equivilent exists and return the number in that phrase
        datenumber = numcheck(text)
        if datenumber != 'X':
            num = datenumber

        #Check to see if the phrase 3rd year or equivilent exists and return the number in that phrase
        
        
        op = " "

        if o in less_than_words:
             op = "<"
        elif o in greater_than_words:
            op = ">"
        elif o in min_words:
            return(where + W + " = (select min(" + W + ") from "+ current_dbfile + ")")
        elif o in max_words:
            return(where + W + " = (select max(" + W + ") from "+ current_dbfile + ")")
        else:
            op = "="

        if num == " ":
            return ""

        
        return( where + W + op + num)
        match = match - 1
    else:
        if span == "":
            return " "
        else:
            return( "No Pattern ")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')