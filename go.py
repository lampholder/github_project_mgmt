import re
import json
import dateutil.parser

from pprint import pprint
from collections import namedtuple

import sqlite3
import requests
from requests.auth import HTTPBasicAuth

from Events import Event


class Timelines(object):
    _url = 'https://api.github.com'
    _auth = HTTPBasicAuth('lampholder', '7f8e955e145d36cfbc43ee01f57a63caa759efe5')

    table_name = 'timelines';
    schema = \
        """
        drop table if exists %s;
        create table %s (
            repo text not null,
            issue number not null,
            date text not null,
            timeline text not null,
            constraint unique_issue unique(repo, issue)
        );
        """ % (table_name, table_name)

    def __init__(self):
        self._db = sqlite3.connect('timelines.db')
        self._db.row_factory = sqlite3.Row
        self._load_schema_if_necessary()

    def _table_exists(self):
        with self._db as connection:
            sql = 'select name from sqlite_master where type=\'table\' and name=?'
            cursor = connection.execute(sql, (self.table_name, ))
            table = cursor.fetchall()
            cursor.close()
            return len(table) == 1

    def _load_schema_if_necessary(self):
        if not self._table_exists():
            with self._db as connection:
                connection.executescript(self.schema)

    def _get_timeline_from_internet(self, issue):
        headers = {'Accept': 'application/vnd.github.mockingbird-preview'}

        url = self._url + '/repos/%s/issues/%d/timeline' % (issue.repo, issue.number)
        while url is not None:
            response = requests.get(url, headers=headers, auth=self._auth)
            url = None

            if response.status_code != 200:
                raise Exception(response.json())

            if 'Link' in response.headers:
                url = re.split('<|>', [link for link in response.headers['Link'].split(',')
                                       if link[-10:] == 'rel="next"'][0])[1]

            for event in response.json():
                yield Event.from_json(event)

    def _get_timeline_from_db(self, issue):
        with self._db as connection:
            cursor = connection.execute('select * from timelines where repo = ? and issue = ?',
                                        (issue.repo, issue.number))
            return cursor.fetchone()

    def _insert_or_replace_timeline_in_db(self, issue, timeline_json):
        with self._db as connection:
            cursor = connection.execute('delete from timelines where repo = ? and issue = ?',
                                        (issue.repo, issue.number))
            cursor = connection.execute('insert into timelines values (?, ?, ?, ?)',
                                        (issue.repo, issue.number, issue.updated_at, timeline_json))

    def get_timeline(self, issue):
        timeline = self._get_timeline_from_db(issue)
        if (timeline is not None and
                dateutil.parser.parse(issue.updated_at) <=
                dateutil.parser.parse(timeline['date'])):
            print 'HIT CACHE!!!'
            for event in json.loads(timeline['timeline']):
                yield Event.from_json(event)
        else:
            timeline = self._get_timeline_from_internet(issue)
            to_write = json.dumps([x.event for x in timeline])
            print 'REPLACING CACHED ITEM!!!'
            self._insert_or_replace_timeline_in_db(issue, to_write)
            for event in timeline:
                yield Event.from_json(event)


class IssueFetcher(object):
    _url = 'https://api.github.com'
    _auth = HTTPBasicAuth('lampholder', '7f8e955e145d36cfbc43ee01f57a63caa759efe5')

    def __init__(self, repos):
        self._repos = repos
        self._timeline = Timelines()

    def search(self, query=None):
        headers = {'Accept': 'application/vnd.github.v3+json'}

        search_url = self._url + '/search/issues'
        params = {'q': ' '.join(['repo:%s' % repo for repo in self._repos]) + ' ' + query}

        while search_url is not None:

            response = requests.get(search_url, headers=headers, params=params, auth=self._auth)
            search_url = None
            params = None

            if response.status_code != 200:
                raise Exception(response.json())

            if 'Link' in response.headers:
                search_url = re.split('<|>', [link for link in response.headers['Link'].split(',')
                                              if link[-10:] == 'rel="next"'][0])[1]

            response_json = response.json()
            issues = response_json['items']

            for issue in issues:
                repo = issue['repository_url'][29:]
                yield json.loads(json.dumps(issue),
                                 object_hook=lambda d: namedtuple('Issue',
                                                                  d.keys() + ['repo'])(*d.values() + [repo]))

    def get_timeline(self, issue):
        return self._timeline.get_timeline(issue)

isf = IssueFetcher(['lampholder/test_data'])
search = isf.search('is:open')
for i in search:
    #print i.title
    #pprint(dict(i._asdict()))
    timeline = isf.get_timeline(i)
    for event in timeline:
        #print(event)
        pass

