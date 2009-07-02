# -*- coding: utf-8 -*-
#
# Copyright (C) 2003-2006 Edgewall Software
# Copyright (C) 2003-2005 Jonas Borgström <jonas@edgewall.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://trac.edgewall.org/wiki/TracLicense.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://trac.edgewall.org/log/.
#
# Author: Jonas Borgström <jonas@edgewall.com>

import os
import re
import time
from trac.util.datefmt import utc
from datetime import datetime
from StringIO import StringIO

from trac.core import *


from trac.config import BoolOption, Option
from trac.env import IEnvironmentSetupParticipant
from trac.ticket import Milestone, Ticket, TicketSystem, ITicketManipulator
from trac.ticket.notification import TicketNotifyEmail
from trac.util import get_reporter_id, escape, Markup
from trac.util.datefmt import format_datetime, pretty_timedelta, http_date
from trac.util.html import html, Markup, Element
from trac.util.text import CRLF, shorten_line
from trac.web import IRequestHandler
from trac.web.chrome import add_link, add_stylesheet, INavigationContributor, ITemplateProvider
from trac.web.main import IRequestHandler
from trac.wiki import wiki_to_html, wiki_to_oneliner, IWikiSyntaxProvider, Formatter
from trac.mimeview.api import Mimeview, IContentConverter
from trac.ticket import web_ui

from trac.ticket.query import QueryModule
from trac.perm import IPermissionRequestor
from trac.ticket import ITicketChangeListener
from trac.search import ISearchSource, search_to_sql, shorten_result

import pkg_resources

from genshi.builder import tag, Element

from trac.config import IntOption

from trac.mimeview import Context
from trac.util.datefmt import format_datetime
from trac.util.presentation import Paginator
from trac.util.translation import _

from trac.web.chrome import add_link, add_stylesheet, INavigationContributor, \
                            ITemplateProvider
from trac.wiki.api import IWikiSyntaxProvider
from trac.wiki.formatter import extract_link


class IShotSearchSource(Interface):
    """
    Extension point interface for adding search sources to the Trac
    Search system.
    """

    def get_search_filters(self, req):
        """
        Return a list of filters that this search source supports. Each
        filter must be a (name, label[, default]) tuple, where `name` is the
        internal name, `label` is a human-readable name for display and
        `default` is an optional boolean for determining whether this filter
        is searchable by default.
        """

    def get_search_results(self, req, terms, filters):
        """
        Return a list of search results matching each search term in `terms`.
        The `filters` parameters is a list of the enabled
        filters, each item being the name of the tuples returned by
        `get_search_events`.

        The events returned by this function must be tuples of the form
        (href, title, date, author, excerpt).
        """

class ShotTicketSystem(TicketSystem):
    implements (IShotSearchSource)

    # ISearchSource methods
    def get_search_filters(self, req):
        if req.perm.has_permission('TICKET_VIEW'):
            yield ('ticket', 'Tickets')
	
    def get_search_results(self, req, terms, filters):
        if not 'ticket' in filters:
            return
        db = self.env.get_db_cnx()
        sql, args = search_to_sql(db, ['b.newvalue'], terms)
        sql2, args2 = search_to_sql(db, ['summary', 'keywords', 'description',
                                         'reporter', 'cc'], terms)
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT a.summary,a.description,a.reporter, "
                       "a.keywords,a.id,a.time,a.status FROM ticket a "
                       "LEFT JOIN ticket_change b ON a.id = b.ticket "
                       "WHERE (b.field='comment' AND %s ) OR %s" % (sql, sql2),
                       args + args2)
        for summary, desc, author, keywords, tid, date, status in cursor:
            ticket = '#%d: ' % tid
            if status == 'closed':
                ticket = Markup('<span style="text-decoration: line-through">'
                                '#%s</span>: ', tid)
            self.log.debug("get_search_results - %s" % summary )
            yield (req.href.ticket(tid),
                  ticket + shorten_line(summary),
                   datetime.fromtimestamp(date,utc), author, shorten_result(desc, terms), summary)

class ShotRedirectModule(Component):
    """
    Converts a URL referencing a shot id to the corresponding URL referencing the ticket for that shot. The result is a page template that redirects to the new page.
    """
    implements(IRequestHandler, ITemplateProvider)

    # IRequestHandler methods
    def match_request(self, req):
        match = re.match('/redirect/(\w\w_\w+)', req.path_info)
        if match:
                req.args['shot_label'] = match.group(1)
                return True
    
    def process_request(self, req):
        # work out ticket based on shot arg
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("SELECT id from ticket where summary = %s", [req.args['shot_label']])
        db.commit()
        data = {}
        for row in cursor:
                data['shot_id'] = row[0]
                self.log.debug("process_request - %s" % row[0])
        return 'redirect.html', data, None
		

    # ITemplateProvider methods
    def get_templates_dirs(self):
        """Return a list of directories containing the provided templates.
        """

        from pkg_resources import resource_filename
        return [resource_filename(__name__, 'templates')]


class ShotSearchModule(Component):

    implements(INavigationContributor, IPermissionRequestor, IRequestHandler,
               ITemplateProvider, IWikiSyntaxProvider)

    search_sources = ExtensionPoint(IShotSearchSource)

    RESULTS_PER_PAGE = 3

    min_query_length = IntOption('search', 'min_query_length', 3,
        """Minimum length of query string allowed when performing a search.""")

    # INavigationContributor methods

    def get_active_navigation_item(self, req):
        return 'search'

    def get_navigation_items(self, req):
        if 'SEARCH_VIEW' in req.perm:
            yield ('mainnav', 'search',
                   tag.a(_('Search'), href=req.href.search(), accesskey=4))

    # IPermissionRequestor methods

    def get_permission_actions(self):
        return ['SEARCH_VIEW']

    # IRequestHandler methods

    def match_request(self, req):
        return re.match(r'/search/?', req.path_info) is not None

    def process_request(self, req):
        req.perm.assert_permission('SEARCH_VIEW')

        if req.path_info == '/search/opensearch':
            return ('opensearch.xml', {},
                    'application/opensearchdescription+xml')

        available_filters = []
        for source in self.search_sources:
            available_filters += source.get_search_filters(req)
        filters = [f[0] for f in available_filters if req.args.has_key(f[0])]
        if not filters:
            filters = [f[0] for f in available_filters
                       if len(f) < 3 or len(f) > 2 and f[2]]
        data = {'filters': [{'name': f[0], 'label': f[1],
                             'active': f[0] in filters}
                            for f in available_filters],
                'quickjump': None,
                'results': []}

        query = req.args.get('q')
        data['query'] = query
        if query:
            data['quickjump'] = self._check_quickjump(req, query)
            if query.startswith('!'):
                query = query[1:]
            terms = self._get_search_terms(query)

            # Refuse queries that obviously would result in a huge result set
            if len(terms) == 1 and len(terms[0]) < self.min_query_length:
                raise TracError(_('Search query too short. Query must be at '
                                  'least %(num)s characters long.',
                                  num=self.min_query_length), _('Search Error'))

            results = []
            for source in self.search_sources:
                results += list(source.get_search_results(req, terms, filters))
            results.sort(lambda x,y: cmp(y[2], x[2]))

            page = int(req.args.get('page', '1'))
            results = Paginator(results, page - 1, self.RESULTS_PER_PAGE)
            for idx, result in enumerate(results):
                self.log.debug("results length- %d" % len(results))
                results[idx] = {'href': result[0], 'title': result[1],
                                'date': format_datetime(result[2]),
                                'author': result[3], 'excerpt': result[4], 'summary' : result[5]}

            pagedata = []    
            data['results'] = results
            shown_pages = results.get_shown_pages(21)
            for shown_page in shown_pages:
                page_href = req.href.search([(f, 'on') for f in filters],
                                            q=req.args.get('q'),
                                            page=shown_page, noquickjump=1)
                pagedata.append([page_href, None, str(shown_page),
                                 'page ' + str(shown_page)])

            fields = ['href', 'class', 'string', 'title','summary']
            results.shown_pages = [dict(zip(fields, p)) for p in pagedata]

            results.current_page = {'href': None, 'class': 'current',
                                    'string': str(results.page + 1),
                                    'title':None}

            if results.has_next_page:
                next_href = req.href.search(zip(filters, ['on'] * len(filters)),
                                            q=req.args.get('q'), page=page + 1,
                                            noquickjump=1)
                add_link(req, 'next', next_href, _('Next Page'))

            if results.has_previous_page:
                prev_href = req.href.search(zip(filters, ['on'] * len(filters)),
                                            q=req.args.get('q'), page=page - 1,
                                            noquickjump=1)
                add_link(req, 'prev', prev_href, _('Previous Page'))

            data['page_href'] = req.href.search(
                zip(filters, ['on'] * len(filters)), q=req.args.get('q'),
                noquickjump=1)

        add_stylesheet(req, 'common/css/search.css')
        return 'search.html', data, None

    # ITemplateProvider methods

    def get_htdocs_dirs(self):
        return []

    def get_templates_dirs(self):
        return [pkg_resources.resource_filename('trac.search', 'templates')]

    # IWikiSyntaxProvider methods

    def get_wiki_syntax(self):
        return []

    def get_link_resolvers(self):
        yield ('search', self._format_link)

    def _format_link(self, formatter, ns, target, label):
        path, query, fragment = formatter.split_link(target)
        if query:
            href = formatter.href.search() + query.replace(' ', '+')
        else:
            href = formatter.href.search(q=path)
        return tag.a(label, class_='search', href=href)

    # Internal methods

    def _check_quickjump(self, req, kwd):
        noquickjump = int(req.args.get('noquickjump', '0'))
        # Source quickjump
        quickjump_href = None
        if kwd[0] == '/':
            quickjump_href = req.href.browser(kwd)
            name = kwd
            description = _('Browse repository path %(path)s', path=kwd)
        else:
            link = extract_link(self.env, Context.from_request(req, 'search'),
                                kwd)
            if isinstance(link, Element):
                quickjump_href = link.attrib.get('href')
                name = link.children
                description = link.attrib.get('title', '')
        if quickjump_href:
            # Only automatically redirect to local quickjump links
            if not quickjump_href.startswith(req.base_path or '/'):
                noquickjump = True
            if noquickjump:
                return {'href': quickjump_href, 'name': tag.EM(name),
                        'description': description}
            else:
                req.redirect(quickjump_href)

    def _get_search_terms(self, query):
        """Break apart a search query into its various search terms.

        Terms are grouped implicitly by word boundary, or explicitly by (single
        or double) quotes.
        """
        results = []
        for term in re.split('(".*?")|(\'.*?\')|(\s+)', query):
            if term != None and term.strip() != '':
                if term[0] == term[-1] == "'" or term[0] == term[-1] == '"':
                    term = term[1:-1]
                results.append(term)
        return results

	