#! /usr/bin/env python2

# SQLAlchemy uses to communicate with various types of DB---APIs and databases.

import os
import sys
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, relationship
from database_setup import Base, Restaurant, MenuItem, User
from flask import Flask, render_template, request, redirect, url_for
from flask import jsonify, flash
from flask import session as login_session
import random
import string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from flask import make_response
import json
import requests
import httplib2

# login_session is working as a dictionary and save data for session when users login.  # noqa
# generate random string namely (state) that identify each session.

app = Flask(__name__)
app.secret_key = 'super_secret_key'


"""
    Oauth is the standard used for authorisation.
    flow object from client_secrets in json file store client_id ,
    client_secret and other Oauth parameters.

    json module provides an api for converting in memory python objects into serializable form called json.  # noqa
"""

CLIENT_ID = json.loads(open('/var/www/catalog/client_secrets.json', 'r').read())['web']['client_id']   # noqa
APPLICATION_NAME = "Restaurant_Item_App"

# Connect to Database and create database session.

engine = create_engine('postgresql://catalog:password@localhost/catalog')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

"""
    The function sessionmaker returns a class, binding the engine passed in the bind parameter.   # noqa
    So, after creating the class, you have to instantiate it.
"""
"""
    state token is created which prevents anti-forgery attacks.
    & store it in a session for later verification and provide security to users.   # noqa
"""


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)
    # return "the current session state is %s" %login_session['state']


@app.route('/menus/JSON')
def menusjson():
    menu = session.query(MenuItem).all()
    if login_session.has_key('email') and login_session['email']:
        return jsonify(menuItems=[i.serialize for i in menu])
    return redirect(url_for('mainpage'))


@app.route('/menus/<int:price>', methods=['GET', 'POST'])
def sort(price):
    prc = session.query(MenuItem).filter_by(price=price)
    return render_template('main.html', menu_item=prc)


@app.route('/menus/<string:name>', methods=['GET', 'POST'])
def sorted(name):
    nam = session.query(MenuItem).filter_by(name=name)
    return render_template('main.html', menu_item=nam)

    """
    Created a function that handles the code sent back from call back method.
    """


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # validating state token
    # *args is used to send a non-keyworded variable length argument list to the function.  # noqa
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    # authorization code is obtained
    try:
        oauth_flow = flow_from_clientsecrets('/var/www/catalog/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

        # checking that the obtained access token is valid
    access_token = credentials.access_token
    login_session['access_token'] = access_token
    print (access_token)
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

        # Only the intended user uses the access_token .
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

        # verifying that the access_token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

        # store the access token in the session for later use.
    # login_session['credentials'] = credentials
    print ('access_token (login)-> ', credentials.access_token)
    login_session['gplus_id'] = gplus_id

    # get user Information through google account.
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if a user exist, if does'nt make a new one.
    user_id = getUserID(login_session['email'])

    print ("before")
    if user_id is None:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    print ("after")

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 250px;
                             height:  250px;
                             border-radius: 56px 55px 0px 200px;
                             -moz-border-radius: 56px 55px 0px 200px;
                             -webkit-border-radius: 56px 55px 0px 200px;
                             border: 0px solid #000000;">
              '''
    # flash("You are now logged in as {name}".format(name=login_session['username'])).   # noqa
    return output


"""
    Disconnect connected user from their google account
    which is done by rejecting the access token.
"""


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    # dumps takes an object and produces a string.
    # credentials is empty then there is no one to disconnect.
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
        # execute http get req to revoke current token.
    access_token = login_session['access_token']
    print ("token -> ", access_token)
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        # disconnecting the users.
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        # Response to indicate users has successfully logout from application.
        print "Successfully disconnected"
        restaurants = session.query(Restaurant).all()
        # Back to lmain page as user should see items even though he has not sign in.   # noqa
        return render_template('restaurant.html', restaurants=restaurants)
    else:
        # For whatever reason, the given token was invalid and something went wrong in disconnect process.   # noqa
        print (login_session['access_token'])
        print "Failed to revoke token for given user."
        return redirect(url_for('mainpage'))


@app.route('/')
@app.route('/menus', methods=['GET', 'POST'])
def mainpage():
    showLogin()
    # menu=session.query(MenuItem).all()
    if login_session.has_key('email') and login_session['email']:
        print "hello"
        flag = 1
        return render_template('restaurant.html', STATE=login_session['state'], name=login_session['username'], image=login_session['picture'])  # noqa
    flag = 0
    if login_session.has_key('email') and login_session['email']:
        flag = 1
        return render_template('restaurant.html', STATE=login_session['state'], name=login_session['username'], image=login_session['picture'])   # noqa
    return render_template('restaurant.html', STATE=login_session['state'], flag=flag, name='', image='')   # noqa


"""
    function which returns JSON APIs to view Restaurant Information.
"""


@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])

"""
    function which returns JSON APIs to view Restaurant Menu Item Information.
"""


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    Menu_Item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/restaurant/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants=[r.serialize for r in restaurants])

"""
    Function shows all restaurant initially present in the database.
"""


@app.route('/restaurant/')
def showRestaurants():
    restaurants = session.query(Restaurant).order_by(asc(Restaurant.name))
    if 'username' not in login_session or login_session['username'] is None:
        login = 0
    else:
        login = 1
    return render_template('restaurant.html', restaurants=restaurants, login_session=login_session, login=login)   # noqa

"""
    Function for adding new restaurant in the database.
"""


@app.route('/restaurant/new/', methods=['GET', 'POST'])
def newRestaurant():
    """
    After you are logged in you need to protect your webpages that
    you want only logged users to access your webpage this can be
    done by verifying login_session has username variable else.
    if you are not logged in  will be redirect to login.html page.
    """
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newRestaurant = Restaurant(
            name=request.form['name'], image=request.form['image'], description=request.form['description'], user_id=login_session['user_id'])   # noqa
        session.add(newRestaurant)
        # flash('New Restaurant %s Successfully Created' % newRestaurant.name)
        flash('New Restaurant {name}  Successfully Created'.format(name=newRestaurant.name))   # noqa
        session.commit()
        return redirect(url_for('showRestaurants'))
    else:
        return render_template('newrestaurant.html')

"""
        Function for deleting new restaurant in the database.
"""


@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    restaurantToDelete = session.query(
        Restaurant).filter_by(id=restaurant_id).one()
    """
    After you are logged in you need to protect your webpages that
    you want only logged users to access your webpage this can be
    done by verifying login_session has username variable else.
    if you are not logged in  will be redirect to login.html page.
    """
    if 'username' not in login_session:
        return redirect('/login')
    if (
        restaurantToDelete and restaurantToDelete.user_id) != (
            login_session['user_id']):
        flash('You are not authorized to delete this restaurant')
        return redirect(url_for('showRestaurants'))
    if request.method == 'POST':
        session.delete(restaurantToDelete)
        flash('{name} Successfully Deleted'.format(name=restaurantToDelete.name))   # noqa
        session.commit()
        return redirect(url_for('showRestaurants', restaurant_id=restaurant_id))   # noqa
    else:
        return render_template(
            'deleterestaurant.html', restaurant=restaurantToDelete)

"""
    Function for editing existing restaurant in the database.
"""


@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    editedRestaurant = session.query(
        Restaurant).filter_by(
            id=restaurant_id).one()
    """
    After you are logged in you need to protect your webpages that
    you want only logged users to access your webpage this can be
    done by verifying login_session has username variable else.
    if you are not logged in  will be redirect to login.html page.
    """
    if 'username' not in login_session:
        return redirect('/login')
    if (
        editedRestaurant and editedRestaurant.user_id) != (
            login_session['user_id']):
        flash('You are not authorized to edit this restaurant')
        return redirect(url_for('showRestaurants'))

    if request.method == 'POST':
        if request.form['name']:
            editedRestaurant.name = request.form['name']
            flash('Restaurant successfully edited {name}'.format(name=editedRestaurant.name))   # noqa
            return redirect(
                url_for('showRestaurants', restaurant_id=restaurant_id))
        else:
            return render_template('editrestaurant.html', restaurant=editedRestaurant)   # noqa

"""
    Function showing the menu of the restaurant.
"""


@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    restaurant = session.query(
        Restaurant).filter_by(
            id=restaurant_id).one()

    if restaurant is None:
        flash("Restaurant does not exist")
        return redirect(url_for('showRestaurants'))

    items = session.query(MenuItem).filter_by(
        restaurant_id=restaurant_id).all()

    # print(login_session['username'])

    if 'username' not in login_session:
        return render_template(
            'main.html',
            items=items,
            restaurant=restaurant)
    else:
        return render_template(
            'menu.html',
            items=items,
            restaurant=restaurant,
            login_session=login_session
            )
"""
    Function to edit the existing menu item.
"""


@app.route(
    '/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit',
    methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    """
    After you are logged in you need to protect your webpages that
    you want only logged users to access your webpage this can be
    done by verifying login_session has username variable else.
    if you are not logged in  will be redirect to login.html page.
    """
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    print (editedItem.user_id)
    print (login_session['user_id'])
    restaurantToDelete = session.query(Restaurant).filter_by(id=restaurant_id).one()   # noqa
    if restaurantToDelete is None:
        flash('This restaurant does not exist')
        return redirect(url_for('showRestaurants'))
    if editedItem is None:
        flash('This item does not exist')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if editedItem.user_id != login_session['user_id']:
        flash('You are not authorized to edit item from this restaurant menu')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['image']:
            editedItem.image = request.form['image']
        if request.form['categories']:
            editedItem.categories = request.form['categories']
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template(
            'editmenuitem.html',
            restaurant_id=restaurant_id,
            menu_id=menu_id, item=editedItem)

"""
    Function create new menu item in the restaurant.
"""


@app.route('/restaurant/<int:restaurant_id>/menu/new/', methods=['GET', 'POST'])   # noqa
def newMenuItem(restaurant_id):
    """
    After you are logged in you need to protect your webpages that
    you want only logged users to access your webpage this can be
    done by verifying login_session has username variable else.
    if you are not logged in  will be redirect to login.html page.

    """
    if 'username' not in login_session:
        return redirect('/login')
    restaurant = session.query(
        Restaurant).filter_by(
            id=restaurant_id).one()
    if restaurant is None:
        flash('This restaurant does not exist')
        return redirect(url_for('showRestaurants'))

    if request.method == 'POST':
        print ("hello")

        newItem = MenuItem(
            name=request.form['name'],
            description=request.form['description'],
            price=request.form['price'],
            image=request.form['image'],
            categories=request.form['category'],
            restaurant_id=restaurant_id,
            user_id=login_session['user_id'])
        session.add(newItem)
        print("added")
        session.commit()
        print ("commited")
        flash('New Menu {name} Item Successfully Created'.format(name=newItem.name))  # noqa
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)

"""
    Function to delete the existing menu item.
"""


@app.route(
    '/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete',
    methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    """
    After you are logged in you need to protect your webpages that
    you want only logged users to access your webpage this can be
    done by verifying login_session has username variable else.
    if you are not logged in  will be redirect to login.html page.
    """
    if 'username' not in login_session:
        return redirect('/login')
    restaurantToDelete = session.query(Restaurant).filter_by(
                                       id=restaurant_id).one()
    if restaurantToDelete is None:
        flash('This restaurant does not exist')
        return redirect(url_for('showRestaurants'))
    itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()

    if itemToDelete is None:
        flash('This item does not exist')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if itemToDelete.user_id != login_session['user_id']:
        flash('You are not authorized to delete item from this restaurant menu')  # noqa
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))

    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    else:
        return render_template('deleteMenuItem.html', item=itemToDelete, restaurant_id=restaurant_id)   # noqa

"""
    Creates a new user and allow him to login.
"""


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

"""
    Created a new user by fetching its email_id.
"""


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
