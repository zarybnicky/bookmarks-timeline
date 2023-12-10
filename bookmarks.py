'''
Inspired by <https://github.com/andrewp-as-is/chrome-bookmarks.py>
'''

from datetime import datetime, timedelta
import json
import os

from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np
import streamlit as st


def process_bookmarks(data: dict):
    urls = []
    folders = []
    for value in data["roots"].values():
        if "children" in value:
            processTree(urls, folders, value["children"])
    return pd.DataFrame(urls)


def processTree(urls, folders, children):
    for item in children:
        if "type" in item and item["type"] == "url":
            url = {
                'id': item['id'],
                'name': item['name'],
                'url': item['url'],
                'date_added': item['date_added'],
                'last_visited': item.get('date_last_used') or item.get("meta_info", {}).get('last_visited_desktop') or item.get("meta_info", {}).get('last_visited'),
            }
            if int(url['last_visited']):
                url['last_visited'] = datetime(1601, 1, 1) + timedelta(microseconds=int(url['last_visited']))
            else:
                url['last_visited'] = None
            url["date_added"] = datetime(1601, 1, 1) + timedelta(microseconds=int(url["date_added"]))
            urls.append(url)

        if "type" in item and item["type"] == "folder":
            folders.append(item)
            if "children" in item:
                processTree(urls, folders, item["children"])


def is_same(user_1, user_2):
    return fuzz.partial_ratio(user_1['name'], user_2['name']) > 90


def main():
    path = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
        df = process_bookmarks(data)

    df.set_index(['date_added'], inplace=True, drop=False)
    df.sort_index(inplace=True, ascending=True)
    df: pd.DataFrame = df.loc[~df['url'].str.contains('youtube.com')]

    st.write(df.loc['2022-12-31':'2023-12-31'])

    by_added = df['date_added'].resample('M').count().rename('added')
    by_visited = df['last_visited'].resample('M').count()
    st.bar_chart(pd.concat([by_added, - by_visited], axis=1))

    # df['real_id'] = find_partitions(df=df, match_func=is_same)
    # df.set_index(['real_id', 'id'], inplace=True)
    # df.sort_index(inplace=True, ascending=True)
    # print(df.loc[df.groupby(df['real_id']).agg('count') > 1])

    # df.loc[df['date_added'].between('2018-12-31', '2019-12-31')]
    # print(df['date_added'].groupby([df.date_added.dt.year, df.date_added.dt.month]).agg('count'))
    # print(df.loc[df['last_visited'].isnull()].describe(datetime_is_numeric=True))


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
