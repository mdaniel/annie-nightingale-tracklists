# -*- coding: utf-8 -*-
from __future__ import print_function
import re
import sys
import urllib
import scraperwiki
from datetime import datetime
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
        artists = []
        for p in performers:
            if p.attrs.get('property', '') == 'foaf:name':
                name = p.text
            else:
                names = p.select('[property="foaf:name"]')
                if not names:
                    print('An artist without a name?\n%s' % repr(p), file=sys.stderr)
                    continue
                name = names[0].text
                del names
            artists.append(name)
            del name
        # have to h3 qualify this because there is dc:title for the Record, too
        title_el = t.select('h3 [property="dc:title"]')
        if title_el:
            title = title_el[0].text
        else:
            title = 'Untitled'  # *shrug*
        record_name = ''
        record_el = t.select('[typeof="mo:Record"]')
        if record_el:
            rec_titles = record_el[0].select('[property="dc:title"]')
            if rec_titles:
                record_name = rec_titles[0].text
            else:
                print('Record with no title?\n%s' % repr(record_el), file=sys.stderr)
        track_el = t.select('.track-number')
        track_num = None
        if track_el:
            try:
                track_num = int(track_el[0].text)
            except ValueError:
                print('Bogus track_number text "%s"' % repr(track_el), file=sys.stderr)
        label_el = t.select('.record-label')
        label = ''
        if label_el:
            label = label_el[0].text
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
    # careful: .weekday() is Monday indexed
    if 5 != datetime.utcnow().weekday():
        return 0
    rows = []
    for u in get_episodes():
        for row in get_listings(u):
            rows.append(row)
    scraperwiki.sqlite.save(unique_keys=['pid'], data=rows)


if __name__ == '__main__':
    main()
