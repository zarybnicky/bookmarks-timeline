'''
Inspired by <https://github.com/andrewp-as-is/chrome-bookmarks.py>
'''

from datetime import datetime, timedelta
import io
import json
import urllib.parse as parse
import os

import altair as alt
from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np
import streamlit as st


def visit_tree(urls, folder):
    for item in folder['children']:
        item_type = item.get('type')
        if item_type == "url":
            url = {
                'id': item['id'],
                'name': item['name'],
                'url': item['url'],
                'folder': folder['name'],
                'date_added': item['date_added'],
                'last_visited': item.get('date_last_used') or item.get("meta_info", {}).get('last_visited_desktop') or item.get("meta_info", {}).get('last_visited'),
            }
            if int(url['last_visited']):
                url['last_visited'] = datetime(1601, 1, 1) + timedelta(microseconds=int(url['last_visited']))
            else:
                url['last_visited'] = None
            url["date_added"] = datetime(1601, 1, 1) + timedelta(microseconds=int(url["date_added"]))
            urls.append(url)

        elif item_type == "folder":
            visit_tree(urls, item)


@st.cache_data
def get_bookmarks():
    path = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        urls = []
        for folder in data["roots"].values():
            visit_tree(urls, folder)
        return pd.DataFrame(urls)


def main():
    st.set_page_config(layout='wide')
    df = get_bookmarks()

    df.set_index(['date_added'], inplace=True, drop=False)
    df.sort_index(inplace=True, ascending=True)

    def simplify_url(url):
        scheme, netloc, path, params, query, fragment = parse.urlparse(url)

        netloc = netloc.removeprefix('en.')
        netloc = netloc.removeprefix('old.')
        netloc = netloc.removeprefix('blog.')
        netloc = netloc.removeprefix('gist.')
        netloc = netloc.removeprefix('www.')
        netloc = netloc.removeprefix('m.')
        netloc = netloc.removeprefix('mobile.')
        if netloc == 'greaterwrong.com':
            return 'lesswrong.com'
        if netloc == 'reddit.com':
            path = path.replace('//', '/')
            netloc = 'reddit.com' + '/'.join(path.split('/')[:3])
        return netloc
    df['site'] = df['url'].apply(simplify_url)

    def categorize(site):
        if site == 'youtube.com':
            return 'YouTube'
        if site in ['reddit.com/r/WormFanfic', 'reddit.com/r/HPfanfiction', 'alternatehistory.com', 'fiction.live', 'scribblehub.com', 'forum.questionablequesting.com', 'forums.sufficientvelocity.com', 'forums.spacebattles.com', 'royalroad.com', 'fanfiction.net', 'archiveofourown.org']:
            return 'Fanfic'
        if site in ['reddit.com/r/Progressivegrowth2', 'alwaysolder.com', 'reddit.com/r/ThickTV', 'reddit.com/r/nsfwcyoa', 'reddit.com/r/UNBGBBIIVCHIDCTIICBG', 'literotica.com', 'writing.com', 'reddit.com/r/BreastExpansion', 'tgstorytime.com', 'tfgames.site', 'deviantart.com', 'girlswithmuscle.com', 'fapello.com', 'chyoa.com', 'f95zone.to', 'mcstories.com']:
            return 'Girls'
        if site in ['ultimate-guitar.com', 'pdfminstrel.files.wordpress.com', 'plihal.wz.cz', 'pisnicky-akordy.cz', 'tabs.ultimate-guitar.com', 'jazzguitar.be', 'classicalguitarshed.com']:
            return 'Guitar'
        if site in ['github.com']:
            return 'Code'
        if site in ['commoncog.com', 'forum.commoncog.com', 'cutlefish.substack.com', 'training.kalzumeus.com']:
            return 'Business'
        if site in ['every.to', 'fortelabs.co']:
            return 'Productivity'
        if site in ['reddit.com/r/maybemaybemaybe', 'reddit.com/r/gifsthatkeepongiving', 'reddit.com/r/PraiseTheCameraMan']:
            return 'Humor'
        return None
    df['category'] = df['site'].apply(categorize)

    with st.sidebar:
        q = st.text_input('Search')
        df = df[df['url'].str.contains(q) | df['name'].str.contains(q)]

        buf = io.StringIO()
        df.info(buf=buf)
        st.text(buf.getvalue())
    st.write(df)

    by_added = df['date_added'].resample('M').count().rename('added')
    by_visited = df['last_visited'].resample('M').count().rename('visited')
    combined = pd.concat([by_added, by_visited], axis=1)

    st.altair_chart(
        alt.Chart(combined.reset_index()).mark_bar().encode(
            x=alt.X('date_added:T'),
            y=alt.Y(alt.repeat("layer"), type="quantitative", stack=False),
            color=alt.datum(alt.repeat("layer")),
        ).repeat(
            layer=['added', 'visited'],
        ),
        use_container_width=True
    )

    last_week = df[df['date_added'] > (datetime.now() - timedelta(days=7))].reset_index(drop=True)
    st.bar_chart(last_week, x='date_added', y=['site'])

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.dataframe(df['site'].value_counts(dropna=False), use_container_width=True)
    with col2:
        st.dataframe(df['folder'].value_counts(dropna=False), use_container_width=True)
    with col3:
        st.dataframe(df['category'].value_counts(dropna=False), use_container_width=True)

    st.markdown('## Missing a category')
    col1, col2 = st.columns([1, 1])
    with col1:
        st.dataframe(df[df['category'].isnull()]['site'].value_counts(), use_container_width=True)
    with col2:
        st.dataframe(df[df['category'].isnull()], use_container_width=True)

    per_site = df['site'].value_counts().to_frame().reset_index().nlargest(100, 'count')
    per_site['label'] = per_site.apply(lambda x: f"{x['site']} ({x['count']})", axis=1)
    points = alt.Chart(per_site).mark_line().encode(
        x=alt.X("site:N", sort='-y', axis=alt.Axis(labels=False)),
        y=alt.Y('count:Q').scale(type='log'),
    )

    st.altair_chart(
        points + points.mark_text(
            align='left',
            baseline='middle',
            dx=7,
            angle=305,
        ).encode(
            text='label'
        ),
        use_container_width=True
    )

    per_folder = df['folder'].value_counts().to_frame().reset_index()
    st.altair_chart(
        alt.Chart(per_folder).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("count:Q"),
            color=alt.Color("folder:N").sort(field='count:Q').scale(scheme="category20"),
            order="count:Q",
        )
    )

    # df['real_id'] = find_partitions(df=df, match_func=is_same)
    # df.set_index(['real_id', 'id'], inplace=True)
    # df.sort_index(inplace=True, ascending=True)
    # print(df.loc[df.groupby(df['real_id']).agg('count') > 1])

    # df.loc[df['date_added'].between('2018-12-31', '2019-12-31')]
    # print(df['date_added'].groupby([df.date_added.dt.year, df.date_added.dt.month]).agg('count'))
    # print(df.loc[df['last_visited'].isnull()].describe(datetime_is_numeric=True))


def is_same(user_1, user_2):
    return fuzz.partial_ratio(user_1['name'], user_2['name']) > 90


def find_partitions(df, match_func, max_size=None, block_by=None):
    """Recursive algorithm for finding duplicates in a DataFrame."""

    # If block_by is provided, then we apply the algorithm to each block and
    # stitch the results back together
    if block_by is not None:
        blocks = df.groupby(block_by).apply(lambda g: find_partitions(
            df=g,
            match_func=match_func,
            max_size=max_size
        ))

        keys = blocks.index.unique(block_by)
        for a, b in zip(keys[:-1], keys[1:]):
            blocks.loc[b, :] += blocks.loc[a].iloc[-1] + 1

        return blocks.reset_index(block_by, drop=True)

    def get_record_index(r):
        return r[df.index.name or 'index']

    records = df.to_records()
    partitions = []
    def find_partition(at=0, partition=None, indexes=None):
        r1 = records[at]
        if partition is None:
            partition = {get_record_index(r1)}
            indexes = [at]
        # Stop if enough duplicates have been found
        if max_size is not None and len(partition) == max_size:
            return partition, indexes

        for i, r2 in enumerate(records):
            if get_record_index(r2) in partition or i == at:
                continue

            if match_func(r1, r2):
                partition.add(get_record_index(r2))
                indexes.append(i)
                find_partition(at=i, partition=partition, indexes=indexes)

        return partition, indexes

    while len(records) > 0:
        partition, indexes = find_partition()
        partitions.append(partition)
        records = np.delete(records, indexes)

    return pd.Series({
        idx: partition_id
        for partition_id, idxs in enumerate(partitions)
        for idx in idxs
    })


if __name__ == "__main__":
    main()
