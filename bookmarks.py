'''
Inspired by <https://github.com/andrewp-as-is/chrome-bookmarks.py>
'''

from datetime import datetime, timezone, timedelta
import json
import os
import sys

import numpy as np
import pandas as pd


class Bookmarks:
    """Bookmarks class. attrs: `path`. properties: `folders`, `urls`"""
    path = None

    def __init__(self, path):
        self.path = path

        attr_list = {"urls": [], "folders": []}
        with open(path, encoding="utf-8") as f:
            self.data = json.load(f)
            for value in self.data["roots"].values():
                if "children" in value:
                    self.processTree(attr_list, value["children"])

        self.urls = attr_list["urls"]
        self.folders = attr_list["folders"]

    def processTree(self, attr, children):
        for item in children:
            if "type" in item and item["type"] == "url":
                if "guid" in item:
                    del item["guid"]
                if "date_last_used" in item:
                    del item["date_last_used"]
                if "meta_info" in item:
                    delta = item["meta_info"].get('last_visited_desktop') or item["meta_info"].get('last_visited')
                    item['last_visited'] = datetime(1601, 1, 1) + timedelta(microseconds=int(delta))
                    del item["meta_info"]
                item["date_added"] = datetime(1601, 1, 1) + timedelta(microseconds=int(item["date_added"]))
                attr["urls"].append(item)

            if "type" in item and item["type"] == "folder":
                attr["folders"].append(item)
                if "children" in item:
                    self.processTree(attr, item["children"])

def main():
    path = os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
    instance = Bookmarks(path)
    df = pd.DataFrame(instance.urls)
    df = df.loc[~df['url'].str.contains('youtube.com')]

    pd.set_option('display.max_rows', None)
    # print(df['date_added'].groupby([df.date_added.dt.year, df.date_added.dt.month]).agg('count'))
    print(df.loc[(df['date_added'] > '2018-12-31') & (df['date_added'] < '2019-12-31')])
    # print(df.loc[df['last_visited'].isnull()].describe(datetime_is_numeric=True))

if __name__ == "__main__":
    main()
