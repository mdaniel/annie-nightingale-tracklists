# -*- coding: utf-8 -*-
from __future__ import print_function
import re
import sys
import urllib
import scraperwiki
from bs4 import BeautifulSoup

def get_episodes():
    broadcasts_url = 'http://www.bbc.co.uk/programmes/b006wkp7/broadcasts'
    html = scraperwiki.scrape(broadcasts_url)
    soup = BeautifulSoup(html)
    episodes = soup.select('[typeof="po:Episode"]')
    for epi in episodes:
        titles = epi.select('[property="dc:title"]')
        if not titles:
            continue
        title = titles[0]
        # this one is a *future* episode, it has not yet been titled
        if re.match(r'\d\d/\d\d/\d\d\d\d', title.text):
            continue
        parent_a = title.parent
        if 'a' != getattr(parent_a, 'name', ''):
            print('Odd, dc:title has no A parent: %s' % repr(title), file=sys.stderr)
            continue
        epi_href = parent_a.attrs.get('href')
        if not epi_href:
            print('Odd, dc:title A has no href: %s' % repr(title), file=sys.stderr)
            continue
        yield urllib.basejoin(broadcasts_url, epi_href)


def get_listings(url):
    html = scraperwiki.scrape(url)
    pid_ma = re.search(r'/programmes/([^/]+)$', url)
    if pid_ma:
        pid = pid_ma.group(1)
    else:
        print('Whoa, bogus URL format you have there: %s' % repr(url), file=sys.stderr)
        pid = url  # *shrug* but pid is the primary key, so it has to be something
    soup = BeautifulSoup(html)
    tracks = soup.select('[typeof="po:MusicSegment"]')
    results = []
    for idx, t in enumerate(tracks):
        about_segment = t.attrs.get('about')
        if about_segment:
            segment_pid_ma = re.search(r'/programmes/([^/#]+)', about_segment)
            segment_pid = segment_pid_ma.group(1)
        else:
            print('Egad, segment has no @about\n%s' % repr(t), file=sys.stderr)
            segment_pid = '%s-number-%d' % (pid, idx)
        performers = t.select('[typeof="mo:MusicArtist"]')
        artists = [p.select('[property="foaf:name"]')[0].text for p in performers]
        # have to h3 qualify this because there is dc:title for the Record, too
        title_el = t.select('h3 [property="dc:title"]')
        if title_el:
            title = title_el[0].text
        else:
            title = 'Untitled'  # *shrug*
        record_el = t.select('[typeof="mo:Record"]')
        if record_el:
            record_name = record_el[0].select('[property="dc:title"]').text
        else:
            record_name = ''
        track_el = t.select('.track-number')
        if track_el:
            track_num = track_el[0].text
        else:
            track_num = None
        label_el = t.select('.record-label')
        if label_el:
            label = label_el[0].text
        else:
            label = ''
        segment = {
            'artists': u'\n'.join(artists),
            'pid': segment_pid,
            'episode_pid': pid,
            'title': title,
            'record_name': record_name,
            'track_num': track_num,
            'label': label,
        }
        yield segment


def main():
    rows = []
    for u in get_episodes():
        for row in get_listings(u):
            rows.append(row)
    scraperwiki.sqlite.save(unique_keys=['pid'], data=rows)


if __name__ == '__main__':
    main()
