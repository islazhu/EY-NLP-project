# Basic flask container
FROM tiangolo/meinheld-gunicorn:python3.8


ADD ./app /home/app/
WORKDIR /home/app/

run pip install flask
run pip install --upgrade pip
run pip install --user -U nltk
run pip install SQLAlchemy
run pip install Flask-SQLAlchemy
run pip install SQLAlchemy-Utils
run pip install pandas
run pip install spacy
run pip install word2number
run python -m spacy download "en_core_web_sm"
run pip install stringcase

ENTRYPOINT ["python3", "app.py"]
