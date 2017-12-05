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
        '/search', 'search',
        '/results', 'results',
        '/view', 'view',
        '/add_bid', 'addbid'
)

class redirect:
    def GET(self, path):
        web.seeother('/' + path)

class index:
    def GET(self):
        return render_template('index.html')

class search:
    def GET(self):
        return render_template('browse.html')
    def POST(self):
        post_params = web.input()
        itemid = post_params['itemid']
        userid = post_params['userid']
        name = post_params['name']
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
            query_dict['sellerid'] = '%' + str(userid) + '%'
        if len(name) > 0:
            query_string += "AND i.name LIKE $name \n"
            query_dict['name'] = '%' + str(name) + '%'
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
    def GET(self, itemid=None):
        if not itemid:
            get_params = web.input(item_id=None)
            itemid = get_params.item_id
        if itemid and itemid != '':
            itemid = int(itemid)
            qd1 = {}
            q1 = """
                SELECT *
                FROM Items i, Auctions a
                WHERE i.item_id = a.item_id
                    AND i.item_id = $item_id
            """
            qd1['item_id'] = itemid
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
            q3 = """
                SELECT * from Bids
                WHERE item_id = $item_id
                ORDER BY time DESC
            """
            bids = sqlitedb.query(q3, qd1)
        else:
            result = None
            status = None
            categories = None
            bids = None
        return render_template('view.html', result=result, status=status, categories=categories,
                               bids = bids)
    def POST(self):
        post_params = web.input()
        t = sqlitedb.transaction()
        try:
            item_id = int(post_params.itemid)
        except ValueError:
            item_id = None
        return self.GET(itemid=item_id)

class addbid:
    def GET(self):
        try:
            get_params = web.input()
            itemID = get_params['itemID']
            return render_template('addbid.html', itemID=itemID)
        except Exception as e:
            return render_template('addbid.html')
    def POST(self):
        post_params = web.input()
        logger.debug('addbid.POST just got an input')
        itemid = post_params['itemID']
        bidderid = post_params['userID']
        bid_amount = post_params['price']
        the_time = sqlitedb.getTime()
        t = sqlitedb.transaction()
        try:
            query_dict = {
                'time': str(the_time),
                'bidder_id': str(bidderid),
                'item_id': int(itemid),
                'amount': float(bid_amount)
            }
            logger.debug(query_dict)
            sqlitedb.db.insert('Bids', **query_dict)
            t.commit()
        except Exception as e:
            t.rollback()
            if str(e) == 'FOREIGN KEY constraint failed':
                e = 'Username not recognized'
            msg = 'Sorry, that was not a legal bid. ERROR: ' + str(e)
            return render_template('addbid.html', message=msg, itemID=itemid, userID=bidderid)
        else:
            msg = 'Your bid is logged. Good luck!'
            return render_template('addbid.html', message=msg)

###########################################################################################
##########################DO NOT CHANGE ANYTHING BELOW THIS LINE!##########################
###########################################################################################

if __name__ == '__main__':
    web.internalerror = web.debugerror
    app = web.application(urls, globals())
    app.add_processor(web.loadhook(sqlitedb.enforceForeignKey))
    app.run()
