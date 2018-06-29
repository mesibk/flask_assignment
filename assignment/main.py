from flask import Flask, request, url_for, redirect

import requests
import json
import datetime
import time
from calendar import timegm


# SQLAlchemy imports
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, and_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

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

    def __init_(self, title, body, uid, authorId, createdAt):
        self.title = title
        self.body = body
        self.uid = uid
        self.rating = 0
        self.lastUpdated = None
        self.commentsCount = 0
        self.votesUp = 0
        self.votesDown = 0
        self.authorId = authorId
        self.createdAt = createdAt

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

    id = Column(Integer, primary_key=True, autoincrement=True)
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
    return authorId[0]


@app.route('/load_data')
def load_data():
    # empty table before everything
    number = 100
    url = 'https://content.guardianapis.com/search?api-key=08bb221a-af15-4f75-b786-daaca0a2635d&show-tags=contributor&page-size={}&q=politics&show-fields=all' \
        .format(str(number))
    data = requests.get(url)
    data = data.json()['response']['results']
    session = Session()
    try:
        for r in data:
            # populate authors table
            if len(r['tags']):
                try:
                    firstName = str(r['tags'][0]['firstName'])
                except KeyError as e:
                    firstName = 'default'
                try:
                    lastName = str(r['tags'][0]['lastName'])
                except KeyError as e:
                    lastName = 'default'
            else:
                firstName = 'default'
                lastName = 'default'

            author = session.query(Author).filter(and_(Author.firstName == firstName, \
                                                       Author.lastName == lastName)).one_or_none()
            if not author:
                newAuthor = Author(firstName=firstName, lastName=lastName)
                session.add(newAuthor)
                session.commit()
    except Exception as e:
        print(type(e))
        return json.dumps({'status': 'Error while adding authors'})

    try:
        for r in data:
            # populate posts table
            if len(r['tags']):
                try:
                    firstName = str(r['tags'][0]['firstName'])
                except KeyError as e:
                    firstName = 'default'
                try:
                    lastName = str(r['tags'][0]['lastName'])
                except KeyError as e:
                    lastName = 'default'
            else:
                firstName = 'default'
                lastName = 'default'
            authorId = get_author_id(firstName, lastName)
            newPost = Posts(title=r['webTitle'].encode('utf-8'),
                            body=r['fields']['body'].encode('utf-8'),
                            uid=r['id'].encode('utf-8'),
                            authorId=authorId,
                            createdAt=r['webPublicationDate'])

            session.add(newPost)
            session.commit()
    except Exception as e:
        print(e)
        return json.dumps({'status': 'Error while adding posts'})

    return json.dumps({'status': 'Data added successfully'})


@app.route('/')
def hello_world():
    r = {"is_claimed": "True", "rating": 3.5}
    return json.dumps(r)


@app.route('/list')
def list_all():
    # add totalRows parameter to 'r'
    page = int(request.args.get('page'))
    session = Session()
    count = session.query(Posts).count()
    r = {}
    r['totalRows'] = count
    r['items'] = []
    if not page:
        results = session.query(Posts).order_by(Posts.rating.desc())
        for res in results:
            d = res.to_dict()
            r['items'].append(d)
    else:
        # for pagination
        # send only number specified by 'pages'
        pageSize = 2
        lower = pageSize*(page-1)
        upper = pageSize*page
        results = session.query(Posts).order_by(Posts.rating.desc())
        results = results.limit(pageSize).offset(pageSize*(page-1)).all()
        for res in results:
            d = res.to_dict()
            r['items'].append(d)

    return json.dumps(r)


@app.route('/comment/<int:postId>', methods=['POST'])
def comment(postId):
    # rating update
    data = request.data.decode('utf-8')
    data = data.replace("'", '"')
    jdata = json.loads(data)
    createdBy = jdata['createdBy']
    comment = jdata['comment']
    postId = int(postId)
    session = Session()
    newComment = Comments(postId=postId, comment=comment, commentBy=createdBy)
    post = session.query(Posts).filter(Posts.id==postId).one_or_none()
    post.commentsCount += 1

    # update post rating
    ranking = post.votesUp + 0.5*post.commentsCount
    diff = datetime.datetime.now() - post.lastUpdated
    diff = diff.total_seconds()
    ranking = ranking*1000/diff
    post.rating = ranking
    post.lastUpdated = datetime.datetime.now()
    try:
        session.add(newComment)
        session.commit()
    except Exception as e:
        print(e)
        res = {'status': 'Comment could not added'}
        return json.dumps(res)
    else:
        # return json status
        res = {'status': 'Comment added successfully'}
        return json.dumps(res)

@app.route('/vote', methods=['POST'])
def vote():
    data = request.data.decode('utf-8')
    data = data.replace("'", '"')
    jdata = json.loads(data)
    session = Session()
    postId = jdata['postId']
    type = jdata['type']
    post = session.query(Posts).filter(Posts.id == postId).one_or_none()
    if int(type) == 1:
        # vote up
        post.votesUp += 1
        # rating formula
        voteCount = post.votesUp
        commentCount = post.commentsCount
    else:
        # vote down
        post.votesDown += 1

    # update post rating
    ranking = post.votesUp + 0.5 * post.commentsCount
    diff = datetime.datetime.now() - post.lastUpdated
    diff = diff.total_seconds()
    ranking = ranking * 1000 / diff
    post.rating = ranking
    post.lastUpdated = datetime.datetime.now()
    try:
        session.commit()
    except Exception as e:
        print(e)
        res = {'status': 'Vote could not added'}
        return json.dumps(res)
    else:
        # return json status
        res = {'status': 'Vote added successfully'}
        return json.dumps(res)


@app.route('/stats')
def stats():
    session = Session()
    commentCount = session.query(Comments).count()
    postsCount = session.query(Posts).count()
    authorCount = session.query(Author).count()
    qry = session.query(Posts.votesUp)
    voteUpCount = qry.with_entities(func.sum(Posts.votesUp)).scalar()
    qry = session.query(Posts.votesDown)
    voteDownCount = qry.with_entities(func.sum(Posts.votesDown)).scalar()
    res = {
        'Comments': int(commentCount),
        'Posts': int(postsCount),
        'Authors': int(authorCount),
        'Vote Ups': int(voteUpCount),
        'Vote Downs': int(voteDownCount)
    }
    return json.dumps(res)

