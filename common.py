import pusher, pusher.gae

import os
import cgi

from flask import Flask, request
from google.appengine.ext import ndb
from google.appengine.ext.ndb import msgprop
from datetime import datetime, timedelta
from protorpc import messages
import logging
import json
import settings
import random

from hashids import Hashids
from counter import increment, get_count

app = Flask(__name__)
app.secret_key = settings.secret_key
app.config.from_object(settings.configClass)

fName = './config.json'
if not os.path.exists(fName): 
    fName = './config.sample.json'
with open(fName) as f:
    config = json.load(f)
app.config.update(config)

pusher_config = app.config.get('pusher')
pusher_key_config = app.config.get('config')

p = pusher.Pusher(
  app_id=pusher_config['PUSHER_APP_ID'],
  key=pusher_key_config['PUSHER_APP_KEY'],
  secret=pusher_config['PUSHER_APP_SECRET'],
  backend=pusher.gae.GAEBackend
)

def generate_user_id():
    hashids = Hashids(salt=settings.HASHID_SALT,min_length=6)
    increment()
    count = get_count()
    hashid = hashids.encode(count)
    return hashid

def generate_color():
    return "#%06x" % random.randint(0, 0xFFFFFF)


def getStudents():
    studentlist = app.config.get('students')
    students = []
    index = 0
    for k, v in studentlist.items():
        student = v
        student['name'] = getStudentName(student)
        if student['enabled'] == 'true':
            student['index'] = index
            students.append(student)
            index+=1
    students = sorted(students, key=lambda student: student['last_name'])
    return students

def getMeetings():
    meetingslist = app.config.get('meetings')
    meetings = []
    index = 0
    for k, v in meetingslist.items():
        meeting = v
        if meeting['enabled'] == 'true':
            meeting['index'] = index
            meetings.append(meeting)
            index+=1
    meetings = sorted(meetings, key=lambda student: student['name'])
    return meetings

def getStudent(studentId):
    students = app.config.get('students')
    if studentId in students:
        return students[studentId]
    return None

def getStudentName(student):
    if student is not None:
        return student['first_name'] + " " + student['last_name']
    return "Anonymous"

def feedUpdated(courseId, new_message):
    p.trigger('feed'+courseId, 'update', {'message': new_message})

def newMessage(courseId, new_message):
    p.trigger('messages'+courseId, 'new_message', new_message)

def newStudentMessage(courseId, studentId, new_message):
    p.trigger('messages'+courseId+studentId, 'new_message', new_message)
    
def registerUpdated(courseId, user):
    p.trigger('feed'+courseId, 'registered', {'user': user})

def loadedUpdated(courseId, user):
    p.trigger('feed'+courseId, 'loaded', {'user': user})

def configChanged(courseId, name, value):
    p.trigger('config'+courseId, 'changed', {name: value})
