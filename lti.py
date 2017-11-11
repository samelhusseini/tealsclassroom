import cgi
from google.appengine.ext import ndb
import ndb_json

from flask import Flask, render_template, session, request, redirect, Response
from pylti.flask import lti
from pylti.common import LTI_SESSION_KEY

import settings
import json

import logging
import urllib

from common import app, p, pusher_key_config
from model import Log, Setting, Student, SourceCode, entity_to_dict, DateTimeJSONEncoder

from common import feedUpdated, registerUpdated, configChanged, loadedUpdated

from canvas_read import CanvasReader

import requests
import requests_toolbelt.adapters.appengine

# Use the App Engine Requests adapter. This makes sure that Requests uses
# URLFetch.
requests_toolbelt.adapters.appengine.monkeypatch()

# ============================================
# Utility Functions
# ============================================

def return_error(msg):
    return render_template('error.html', msg=msg)


def error(exception=None):
    app.logger.error("PyLTI error: {}".format(exception))
    return return_error('''Authentication error,
        please refresh and try again. If this error persists,
        please contact support.''')


# ============================================
# Web Views / Routes
# ============================================

# LTI Launch
@app.route('/launch', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='any', app=app)
def launch(lti=lti):
    """
    Returns the launch page
    request.form will contain all the lti params
    """

    # example of getting lti data from the request
    # let's just store it in our session
    session['full_name'] = request.form.get('lis_person_name_full')

    # Write the lti params to the console
    app.logger.info(json.dumps(request.form, indent=2))

    session['guid'] = request.form.get('tool_consumer_instance_guid')
    session['course_id'] = request.form.get('custom_canvas_course_id')
    session['user_id'] = request.form.get('custom_canvas_user_id')

    roles = request.form.get('roles')
    session['user_image'] = request.form.get('user_image')

    session[LTI_SESSION_KEY] = True
    session['oauth_consumer_key'] = settings.CONSUMER_KEY

    if 'Learner' in roles.split(','):
        session['roles'] = 'Student'
        return redirect("/student")

    if 'Instructor' in roles.split(','):
        session['roles'] = 'Instructor'
        return redirect("/admin")

    return render_template('ltiindex.html', lis_person_name_full=session['lis_person_name_full'])

# Student Launch
@app.route("/student", methods=['POST', 'GET'])
@lti(request='session', error=error, role='any', app=app)
def student(lti=lti):
    jsonsession = {
        'guid': session['guid'],
        'course_id': session['course_id'],
        'user_id': session['user_id'],
        'full_name': session['full_name'],
        'user_image': session['user_image'],
        'role': session['roles']
    }
    classSkype = ndb.Key('Setting', session['course_id'] + 'classSkype').get()
    iframeUrl = ndb.Key('Setting', session['course_id'] + 'iframeUrl').get()
    jsonconfig = {
        'PUSHER_APP_KEY': json.dumps(pusher_key_config['PUSHER_APP_KEY']).replace('"', ''),
        'iframeUrl': json.dumps(iframeUrl.value).replace('"', '') if iframeUrl else '',
        'classSkype': json.dumps(classSkype.value).replace('"', '') if classSkype else ''
    }
    if session['roles'] == "Student":
        student = ndb.Key('Student', session['course_id'] + session['user_id']).get()
        if (student and student.primaryRemoteLink):
            jsonsession['remote_link'] = json.dumps(student.primaryRemoteLink).replace('"', '')
        host = app.config.get('host')
        trigger_loaded(session['course_id'], session['user_id'])
        return render_template('index.html', jsconfig=json.dumps(jsonconfig), jssession=json.dumps(jsonsession), host=host)
    if session['roles'] == "Instructor":
        host = app.config.get('host')
        return render_template('index.html', jsconfig=json.dumps(jsonconfig), jssession=json.dumps(jsonsession), host=host)
    return "Please launch Remote Class to verify login"



# Instructor Launch
@app.route("/admin", methods=['POST', 'GET'])
@lti(request='session', error=error, role='staff', app=app)
def admin(lti=lti):
    jsonsession = {
        'guid': session['guid'],
        'course_id': session['course_id'],
        'user_id': session['user_id'],
        'full_name': session['full_name'],
        'user_image': session['user_image'],
        'role': session['roles']
    }
    classSkype = ndb.Key('Setting', session['course_id'] + 'classSkype').get()
    iframeUrl = ndb.Key('Setting', session['course_id'] + 'iframeUrl').get()
    jsonconfig = {
        'PUSHER_APP_KEY': json.dumps(pusher_key_config['PUSHER_APP_KEY']).replace('"', ''),
        'iframeUrl': json.dumps(iframeUrl.value).replace('"', '') if iframeUrl else '',
        'classSkype': json.dumps(classSkype.value).replace('"', '') if classSkype else ''
    }
    host = app.config.get('host')
    return render_template('admin.html', jsconfig=json.dumps(jsonconfig), jssession=json.dumps(jsonsession), host=host)



# LTI Launch
@app.route('/launch_class', methods=['POST', 'GET'])
@lti(error=error, request='initial', role='any', app=app)
def launch_class(lti=lti):
    """
    Returns the launch page
    request.form will contain all the lti params
    """
    session['course_id'] = request.form.get('custom_canvas_course_id')
    session['user_id'] = request.form.get('custom_canvas_user_id')
    roles = request.form.get('roles')

    if 'Learner' in roles.split(','):
        student = ndb.Key('Student', session['course_id'] + session['user_id']).get()
        if (student and student.primaryRemoteLink):
            return redirect(json.dumps(student.primaryRemoteLink).replace('"', ''))

    if 'Instructor' in roles.split(','):
        session['roles'] = 'Instructor'
        return redirect("https://meet.lync.com/microsoft/samelh/37BHT9O9")
    
    app.logger.error("Error with Classroom session.")
    return return_error('''Error with Classroom session. Please refresh and try again. If this error persists,
        please contact support.''')

# LTI XML Configuration
@app.route("/xml/", methods=['GET'])
def xml():
    """
    Returns the lti.xml file for the app.
    """
    try:
        return Response(render_template(
            'lti.xml'), mimetype='application/xml'
        )
    except:
        app.logger.error("Error with XML.")
        return return_error('''Error with XML. Please refresh and try again. If this error persists,
            please contact support.''')

# LTI XML Configuration
@app.route("/xml_class/", methods=['GET'])
def xml_class():
    """
    Returns the lti.xml file for the app.
    """
    try:
        return Response(render_template(
            'class.xml'), mimetype='application/xml'
        )
    except:
        app.logger.error("Error with XML.")
        return return_error('''Error with XML. Please refresh and try again. If this error persists,
            please contact support.''')

@app.route("/importusers", methods=['POST'])
#@lti(request='session', error=error, role='staff', app=app)
#def import_users(lti=lti):
def import_users():
    content = request.get_json(silent=True)
    oauth_token = cgi.escape(content['token'])
    courseId = cgi.escape(content['courseId'])
    base_url = "https://canvas.instructure.com"
    api_prefix = "/api/v1"
    canvas = CanvasReader(oauth_token, base_url, api_prefix, verbose=True)
    users = canvas.get_users(courseId)
    for user in users:
        studentId = str(user['id'])
        user_info = canvas.get_user_profile(studentId)
        logging.info(user_info)
        shortName = user['short_name']
        avatarUrl = user_info['avatar_url']
        key = courseId + studentId
        student = Student.get_or_insert(key, studentId=studentId, courseId=courseId, fullName=shortName, avatarUrl=avatarUrl)
        student.fullName = shortName
        student.avatarUrl = avatarUrl
        student.put()
    configChanged(courseId, 'config', 'users')
    return ""


@app.route("/feed", methods=['POST'])
#@lti(request='session', error=error, role='staff', app=app)
#def get_feed(lti=lti):
def get_feed():
    content = request.get_json(silent=True)
    courseId = cgi.escape(content['courseId'])
    feeds = Log.get_by_course(courseId)
    jsonfeeds = []
    for feed in feeds:
        jsonfeed = entity_to_dict(feed, ['student', 'type'], ['date', 'key'])
        jsonfeed["date"] = DateTimeJSONEncoder().encode(feed.date).replace('"', '')
        student = ndb.Key('Student', courseId + feed.student).get()
        if (student):
            jsonfeed["fullName"] = student.fullName
            jsonfeed["avatarUrl"] = student.avatarUrl
        jsonfeeds.append(jsonfeed)
    return json.dumps(jsonfeeds)

@app.route("/users", methods=['POST'])
#@lti(request='session', error=error, role='staff', app=app)
#def get_users(lti=lti):
def get_users():
    content = request.get_json(silent=True)
    courseId = cgi.escape(content['courseId'])
    users = Student.get_by_course(courseId)
    return users

@app.route("/delete_user", methods=['POST'])
@lti(request='session', error=error, role='staff', app=app)
def delete_user(lti=lti):
    content = request.get_json(silent=True)
    studentId = cgi.escape(content['studentId'])
    courseId = cgi.escape(content['courseId'])
    student_key = ndb.Key('Student', courseId + studentId)
    student_key.delete()
    configChanged(courseId, 'config', 'users')
    return "Deleted"

@app.route("/update_primary", methods=['POST'])
@lti(request='session', error=error, role='staff', app=app)
def update_primary(lti=lti):
#def update_primary():
    content = request.get_json(silent=True)
    studentId = cgi.escape(content['studentId'])
    courseId = cgi.escape(content['courseId'])
    primaryLink = cgi.escape(content['primaryLink'])
    student = ndb.Key('Student', courseId + studentId).get()
    student.primaryRemoteLink = primaryLink
    student.put()
    configChanged(courseId, 'config', 'users')
    return "Updated primary"

@app.route("/update_secondary", methods=['POST'])
@lti(request='session', error=error, role='staff', app=app)
def update_secondary(lti=lti):
    content = request.get_json(silent=True)
    studentId = cgi.escape(content['studentId'])
    courseId = cgi.escape(content['courseId'])
    secondaryLink = cgi.escape(content['secondaryLink'])
    student = ndb.Key('Student', courseId + studentId).get()
    student.secondaryRemoteLink = secondaryLink
    student.put()
    configChanged(courseId, 'config', 'users')
    return "Updated primary"

@app.route("/update_settings", methods=['POST'])
@lti(request='session', error=error, role='staff', app=app)
def update_settings(lti=lti):
#def update_settings():
    content = request.get_json(silent=True)
    courseId = cgi.escape(content['courseId'])
    name = cgi.escape(content['settingName'])
    value = cgi.escape(content['settingValue'])
    setting = Setting.get_or_insert(courseId + name, courseId=courseId, name=name, value=value)
    setting.value = value
    setting.put()
    configChanged(courseId, name, value)
    return "Updated settings"

@app.route("/help", methods=['POST'])
@lti(request='session', error=error, role='student', app=app)
def trigger_help(lti=lti):
#def trigger_help():
    content = request.get_json(silent=True)
    logging.info(content)
    studentId = cgi.escape(content['studentId'])
    studentName = cgi.escape(content['studentName'])
    courseId = cgi.escape(content['courseId'])

    student = ndb.Key('Student', courseId + studentId).get()
    help = Log(type='help', courseId=courseId, student=studentId)
    help.put()

    fullName = student.fullName if student else 'Unknown student'
    avatarUrl = student.avatarUrl if student else ''

    feedUpdated(courseId, {
        'student': studentId,
        'fullName': fullName,
        'avatarUrl': avatarUrl
    })
    return "Help received"

@app.route("/register", methods=['POST'])
@lti(request='session', error=error, role='student', app=app)
def trigger_register(lti=lti):
    content = request.get_json(silent=True)
    studentId = cgi.escape(content['studentId'])
    courseId = cgi.escape(content['courseId'])

    register = Log(type='registered', courseId=courseId, student=studentId)
    register.put()

    registerUpdated(courseId, {
        'student': studentId
    })
    return "Registration received"


def trigger_loaded(courseId, studentId):
    loaded = Log(type='loaded', courseId=courseId, student=studentId)
    loaded.put()

    loadedUpdated(courseId, {
        'student': studentId
    })

# SNAP CLOUD
@app.route("/SnapCloud", methods=['POST'])
def SNAP_login():
    content = request.get_json(silent=True)
    username = cgi.escape(content["__u"])
    password = cgi.escape(content["__h"])
    if (password == "CHANGEME"):
        return Response(render_template(
            'SNAP_API.txt'),
            headers={'MioCracker': username}
        )
    return ""

@app.route("/SnapCloudRawPublic", methods=['GET'])
def SNAP_Public():
    Username = cgi.escape(request.args.get('Username'))
    ProjectName = cgi.escape(request.args.get('ProjectName'))
    code = ndb.Key('SourceCode', Username + ProjectName).get()
    sourceCode = str(code.sourceCode) if code.sourceCode is not None else ""
    media = str(code.media) if code.media is not None else "<media name=\"" + ProjectName + "\" app=\"Snap! 4.0, http://snap.berkeley.edu\" version=\"1\"></media>"
    return Response("<snapdata>" + sourceCode + media + "</snapdata>", headers={'Content-Type': 'text/html; charset=UTF-8'})

@app.route("/SnapCloud/<URL>", methods=['GET', 'POST'])
def SNAP_Service(URL):
    # Save project
    studentKey = request.headers['MioCracker'] #'8791939'

    if (URL[0:4] == ".1.0"):
        ProjectName = cgi.escape(request.form["ProjectName"])
        Source = request.form["SourceCode"]
        Media = request.form["Media"]
        SourceSize = cgi.escape(request.form["SourceSize"])
        MediaSize = cgi.escape(request.form["MediaSize"])
        key = studentKey + ProjectName
        code = SourceCode.get_or_insert(key, studentKey=studentKey, projectName=ProjectName, sourceCode=Source)
        code.sourceCode = Source
        code.media = Media
        code.sourceSize = SourceSize
        code.mediaSize = MediaSize
        code.put()
        return key
    # Get project list
    if (URL[0:4] == ".2.0"):
        # Retrieve all code
        all_code = SourceCode.get_all(studentKey)
        retVal = []
        for code in all_code:
            projectName = code.projectName.encode('utf-8')
            updated = ""
            notes = ""
            logging.info(projectName)
            retVal.append("ProjectName=" + urllib.quote(projectName) + "&Updated=" + updated + "&Notes=" + notes + "&Public=true")
            logging.info(retVal)
        return " ".join(retVal)
    # Get project
    if (URL[0:4] == ".3.0"):
        return "Not Supported"
    # Get raw project
    if (URL[0:4] == ".4.0"):
        ProjectName = cgi.escape(request.form["ProjectName"])
        code = ndb.Key('SourceCode', studentKey + ProjectName).get()
        sourceCode = str(code.sourceCode) if code.sourceCode is not None else ""
        media = str(code.media) if code.media is not None else "<media name=\"" + ProjectName + "\" app=\"Snap! 4.0, http://snap.berkeley.edu\" version=\"1\"></media>"
        return Response("<snapdata>" + sourceCode + media + "</snapdata>", headers={'Content-Type': 'text/plain'})
    # Delete project
    if (URL[0:4] == ".5.0"):
        ProjectName = cgi.escape(request.form["ProjectName"])
        code = ndb.Key('SourceCode', studentKey + ProjectName)
        code.delete()
        return ""
    # Publish project
    if (URL[0:4] == ".6.0"):
        return "Not supported"
    # Unpublish project
    if (URL[0:4] == ".7.0"):
        return "Not supported"
    # Logout
    if (URL[0:4] == ".8.0"):
        return "Not supported"
    # Change password
    if (URL[0:4] == ".9.0"):
        return "Not supported"
    return "Unknown API call"