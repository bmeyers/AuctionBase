#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
import sqlitedb
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

import logging
logging.basicConfig(filename='log_file.log', level=logging.DEBUG)
logger = logging.getLogger(__name__)

###########################################################################################
##########################DO NOT CHANGE ANYTHING ABOVE THIS LINE!##########################
###########################################################################################

######################BEGIN HELPER METHODS######################

# helper method to convert times from database (which will return a string)
# into datetime objects. This will allow you to compare times correctly (using
# ==, !=, <, >, etc.) instead of lexicographically as strings.

# Sample use:
# current_time = string_to_time(sqlitedb.getTime())

def string_to_time(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

# helper method to render a template in the templates/ directory
#
# `template_name': name of template file to render
#
# `**context': a dictionary of variable names mapped to values
# that is passed to Jinja2's templating engine
#
# See curr_time's `GET' method for sample usage
#
# WARNING: DO NOT CHANGE THIS METHOD
def render_template(template_name, **context):
    extensions = context.pop('extensions', [])
    globals = context.pop('globals', {})

    jinja_env = Environment(autoescape=True,
            loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
            extensions=extensions,
            )
    jinja_env.globals.update(globals)

    web.header('Content-Type','text/html; charset=utf-8', unique=True)

    return jinja_env.get_template(template_name).render(context)

#####################END HELPER METHODS#####################
# first parameter => URL, second parameter => class name
urls = ('/', 'index',
        '/currtime', 'curr_time',
        '/selecttime', 'select_time',
        '/browse', 'browse'
)

class index:
    def GET(self):
        return render_template('index.html')

class browse:
    def GET(self):
        return render_template('browse.html')
    def POST(self):
        post_params = web.input()
        itemid = post_params['itemid']
        userid = post_params['userid']
        category = post_params['category']
        description = post_params['description']
        minprice = post_params['minprice']
        maxprice = post_params['maxprice']
        status = post_params['status']
        print(status)

        query_string = """
            SELECT i.name, i.item_id, a.currently
            FROM Items i, Auctions a
            WHERE i.item_id = a.item_id
        """
        query_dict = {}
        if len(itemid) > 0:
            query_string += "AND i.item_id LIKE $itemid \n"
            query_dict['itemid'] = '%' + str(itemid) + '%'
        query_string += 'LIMIT 10;'
        results = sqlitedb.query(query_string, query_dict)
        return render_template('results.html', query= query_string, results=results)

class curr_time:
    # A simple GET request, to '/currtime'
    #
    # Notice that we pass in `current_time' to our `render_template' call
    # in order to have its value displayed on the web page
    def GET(self):
        current_time = sqlitedb.getTime()
        return render_template('curr_time.html', time = current_time)

class select_time:
    # Another GET request, this time to the URL '/selecttime'
    def GET(self):
        return render_template('select_time.html')

    # A POST request
    #
    # You can fetch the parameters passed to the URL
    # by calling `web.input()' for **both** POST requests
    # and GET requests
    def POST(self):
        post_params = web.input()
        logger.debug('select_time.POST just got an input')
        MM = post_params['MM']
        dd = post_params['dd']
        yyyy = post_params['yyyy']
        HH = post_params['HH']
        mm = post_params['mm']
        ss = post_params['ss'];
        enter_name = post_params['entername']


        selected_time = '%s-%s-%s %s:%s:%s' % (yyyy, MM, dd, HH, mm, ss)
        update_message = '(Hello, %s. Previously selected time was: %s.)' % (enter_name, selected_time)
        # save the selected time as the current time in the database
        t = sqlitedb.transaction()
        try:
            query_string = "update CurrentTime set the_time = $selected_time"
            sqlitedb.query(query_string, {'selected_time': selected_time})
        except Exception as e:
            t.rollback()
            msg = 'tried to update time to '+selected_time+'\nERROR: '+str(e)
            return render_template('select_time.html', message=msg)
        else:
            t.commit()
            return render_template('select_time.html', message=update_message)

###########################################################################################
##########################DO NOT CHANGE ANYTHING BELOW THIS LINE!##########################
###########################################################################################

if __name__ == '__main__':
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.add_processor(web.loadhook(sqlitedb.enforceForeignKey))
    app.run()
