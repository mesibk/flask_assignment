from flask import Flask, request, url_for, redirect

import requests
import json
import datetime
import socket

# SQLAlchemy imports
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, and_
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
app = Flask(__name__)
engine = create_engine('mysql://root:root@127.0.0.1/db')
Session = sessionmaker(bind=engine)



class Posts(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String)
    body = Column(String)
    uid = Column(Integer)
    rating = Column(Float, default=0)
    lastUpdated = Column(TIMESTAMP)
    commentsCount = Column(Integer, default=0)
    votesUp = Column(Integer, default=0)
    votesDown = Column(Integer, default=0)
    authorId = Column(Integer)
    createdAt = Column(TIMESTAMP)

    def __init_(self, title, body, uid, authorId):
        self.title = title
        self.body = body
        self.uid = uid
        self.rating = 0
        self.lastUpdated = None
        self.commentsCount = 0
        self.votesUp = 0
        self.votesDown = 0
        self.authorId = authorId
        self.createdAt = datetime.datetime.now

    def to_dict(self):
        row_dict = {}
        for column in self.__table__.columns:
            if isinstance(column.type, sqlalchemy.sql.sqltypes.TIMESTAMP):
                value = getattr(self, column.name)
                row_dict[column.name] = value.isoformat()
            else:
                value = getattr(self, column.name)
                row_dict[column.name] = value
        return row_dict


class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True, autoincrement=True, default=1)
    postId = Column(Integer)
    comment = Column(String)
    commentBy = Column(String)
    addedOn = Column(TIMESTAMP)

    def __init__(self, postId, comment, commentBy):
        self.postId = postId
        self.comment = comment
        self.commentBy = commentBy
        self.addedOn = datetime.datetime.now()

    def to_dict(self):
        row_dict = {}
        for column in self.__table__.columns:
            if isinstance(column.type, sqlalchemy.sql.sqltypes.TIMESTAMP):
                value = getattr(self, column.name)
                row_dict[column.name] = value.isoformat()
            else:
                value = getattr(self, column.name)
                row_dict[column.name] = value
        return row_dict


class Author(Base):
    __tablename__ = 'author'

    id = Column(Integer, primary_key=True)
    firstName = Column(String)
    lastName = Column(String)

    def __init__(self, firstName, lastName):
        self.firstName = firstName
        self.lastName = lastName

    def to_dict(self):
        row_dict = {}
        for column in self.__table__.columns:
            if isinstance(column.type, sqlalchemy.sql.sqltypes.TIMESTAMP):
                value = getattr(self, column.name)
                row_dict[column.name] = value.isoformat()
            else:
                value = getattr(self, column.name)
                row_dict[column.name] = value
        return row_dict


def get_author_id(firstName, lastName):
    session = Session()
    authorId = session.query(Author.id).filter( \
                and_(Author.firstName == firstName, \
                Author.lastName == lastName)).one_or_none()
    #print(authorId)
    return authorId[0]


@app.route('/load_data')
def load_data():
    # empty table before everything
    number = 2
    url = 'https://content.guardianapis.com/search?api-key=08bb221a-af15-4f75-b786-daaca0a2635d&show-tags=contributor&page-size={}&q=politics&show-fields=all' \
        .format(str(number))
    data = requests.get(url)
    data = data.json()['response']['results']
    session = Session()
    for r in data:
        # populate authors table
        firstName = str(r['tags'][0]['firstName'])
        lastName = str(r['tags'][0]['lastName'])
        author = session.query(Author).filter(and_(Author.firstName == firstName, \
                                                   Author.lastName == lastName)).first()
        if not author:
            #print(firstName)
            #print(lastName)
            newAuthor = Author(firstName=firstName, lastName=lastName)
            session.add(newAuthor)
            session.commit()

    for r in data:
        # populate posts table
        firstName = str(r['tags'][0]['firstName'])
        lastName = str(r['tags'][0]['lastName'])
        authorId = get_author_id(firstName, lastName)
        #print(r['fields']['body'])
        newPost = Posts(title=r['webTitle'],
                        body=r['fields']['body'].encode('utf-8'),
                        uid=r['id'],
                        authorId=authorId)
        session.add(newPost)
        session.commit()

    return str(data)

@app.route('/')
def hello_world():
    return "Hello, world"


@app.route('/list')
def list_all():
    # add totalRows parameter to 'r'
    page = request.args.get('page')
    session = Session()
    count = session.query(Posts).count()
    if not page:
        results = session.query(Posts).order_by(Posts.rating.desc())
        r = {}
        r['totalRows'] = count
        r['items'] = []
        for res in results:
            d = res.to_dict()
            res = json.dumps(d)
            r['items'].append(res)
    else:
        # for pagination
        # send only number specified by 'pages'
        pass
    return json.dumps(r)


@app.route('/comment', methods=['POST'])
def comment():
    # rating update
    data = request.data.decode('utf-8')
    data = data.replace("'", '"')
    jdata = json.loads(data)
    createdBy = jdata['createdBy']
    comment = jdata['comment']
    postId = jdata['postId']

    session = Session()
    comment = Comments(postId=postId, comment=comment, commentBy=createdBy)
    try:
        session.add(comment)
        session.commit()
    except Exception as e:
        #print(e)
        print("Comment could not be added")
    else:
        return redirect(url_for('list_all'))
        # return json status


@app.route('/vote', methods=['POST'])
def vote():
    session = Session()
    post = session.query(Posts).filter(Posts.id==request.form['postId'])
    if int(request.form['type']) == 1:
        # vote up
        post.votesUp += 1
        # rating formula
    else:
        # vote down
        post.votesDown += 1

    session.commit()
    return redirect(url_for('list_all'))
    # return json status

