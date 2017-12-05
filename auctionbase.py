#!/usr/bin/env python

import sys; sys.path.insert(0, 'lib') # this line is necessary for the rest
import os                             # of the imports to work!

import web
import sqlitedb
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from ast import literal_eval
import logging
logging.basicConfig(filename='log_file.log', level=logging.INFO)
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
urls = ('/(.*)/', 'redirect',
        '/', 'index',
        '/currtime', 'curr_time',
        '/selecttime', 'select_time',
        '/browse', 'browse',
        '/results', 'results',
        '/view', 'view'
)

class redirect:
    def GET(self, path):
        web.seeother('/' + path)

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


        query_dict = {}
        current_time = sqlitedb.getTime()
        if len(category) > 0:
            query_string = """
                        SELECT i.name, i.item_id, a.seller_id, a.currently, a.number_of_bids
                        FROM Items i, Auctions a, Categories c
                        WHERE i.item_id = a.item_id
                        AND i.item_id = c.item_id
                    """
            query_string += "AND c.category_name LIKE $category \n"
            query_dict['category'] = '%' + str(category) + '%'
        else:
            query_string = """
                        SELECT i.name, i.item_id, a.seller_id, a.currently, a.number_of_bids
                        FROM Items i, Auctions a
                        WHERE i.item_id = a.item_id
                    """
        if len(itemid) > 0:
            query_string += "AND i.item_id LIKE $itemid \n"
            query_dict['itemid'] = '%' + str(itemid) + '%'
        if len(userid) > 0:
            query_string += "AND a.seller_id LIKE $sellerid \n"
            query_dict['sellerid'] = userid
        if len(description) > 0:
            query_string += "AND i.description LIKE $description \n"
            query_dict['description'] = '%' + str(description) + '%'
        if len(minprice) > 0:
            query_string += "AND a.currently > $minprice \n"
            query_dict['minprice'] = minprice
        if len(maxprice) > 0:
            query_string += "AND a.currently < $maxprice \n"
            query_dict['maxprice'] = maxprice
        if status == 'all':
            pass
        elif status == 'open':
            query_string += "AND a.started <= $the_time and a.ends > $the_time \n"
            query_dict['the_time'] = current_time
        elif status == 'closed':
            query_string += "AND a.ends <= $the_time \n"
            query_dict['the_time'] = current_time
        elif status == 'not started':
            query_string += "AND a.started > $the_time \n"
            query_dict['the_time'] = current_time

        query_string += 'LIMIT 50'
        results = sqlitedb.query(query_string, query_dict)
        page = 1
        query_string = ' '.join(query_string.split())
        return render_template('results.html', query= query_string, results=results, query_dict=query_dict, page=page)

class results:
    def GET(self):
        get_params = web.input(query=None, results=None, page=None, query_dict=None)
        query = get_params.query
        query_dict = literal_eval(get_params.query_dict)
        results = get_params.results
        page = int(get_params.page)
        logging.debug(str(query)+' '+str(results))
        if page == 1:
            results = sqlitedb.query(query, query_dict)
        else:
            offset = (page - 1) * 50
            query_dict['offset'] = offset
            results = sqlitedb.query(query+'\n OFFSET $offset', query_dict)
        return render_template('results.html', query=query, query_dict=query_dict, results=results, page=page)

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

class view:
    def GET(self, item_id=None):
        if not item_id:
            get_params = web.input(item_id=None)
            item_id = get_params.item_id
        if item_id:
            item_id = int(item_id)
            qd1 = {}
            q1 = """
                SELECT *
                FROM Items i, Auctions a
                WHERE i.item_id = a.item_id
                    AND i.item_id = $item_id
            """
            qd1['item_id'] = item_id
            result = sqlitedb.query(q1, qd1)
            current_time = string_to_time(sqlitedb.getTime())
            start_time = string_to_time(result[0].started)
            end_time = string_to_time(result[0].ends)
            if start_time <= current_time and end_time > current_time:
                status = 'open'
            elif start_time <= current_time and end_time <= current_time:
                status = 'closed'
            else:
                status = 'not yet started'
            q2 = """
                SELECT category_name
                FROM Categories
                WHERE item_id = $item_id
            """
            categories = sqlitedb.query(q2, qd1)
        else:
            result = None
            status = None
            categories = None
        return render_template('view.html', result=result, status=status, categories=categories)
    def POST(self):
        post_params = web.input()
        item_id = int(post_params.itemid)
        return self.GET(item_id=item_id)

###########################################################################################
##########################DO NOT CHANGE ANYTHING BELOW THIS LINE!##########################
###########################################################################################

if __name__ == '__main__':
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.add_processor(web.loadhook(sqlitedb.enforceForeignKey))
    app.run()
