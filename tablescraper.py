# Ian London 2016
# ianlondon.github.io
#
# A library for extracting HTML tables to pandas dataframes

from lxml import html
from lxml.etree import tostring as html_to_string
import requests
import pandas as pd
from collections import Sequence

def to_sequence(x):
    """
    Makes sure an object is a sequence and if it's not, return a 1-tuple containing that object.
    Useful if you want to take an argument which might be one element and might be a list or tuple
    """
    if isinstance(x, Sequence):
        return x
    return (x,)

def url_to_tree(url):
    try:
        page = requests.get(url)
    except requests.ConnectionError as e:
        print 'Could not connect to url {url}: {e}'.format(url=url,e=e)
        return

    if page.status_code != 200:
        print '{res}: could not get url {url}'.format(res=page.response, url=url)
        return

    tree = html.fromstring(page.content)
    return tree


def df_from_tables(table_els, header=None, skiprows=1):
    """
    From a single lxml.html.HtmlElement <table> or a sequence of them,
    convert to pandas DataFrame and optionally skip rows and set the header.
    """

    dfs = []
    table_els = to_sequence(table_els)

    for table_el in table_els:
        tables = pd.read_html(html_to_string(table_el), match='', skiprows=skiprows)

        if len(tables) != 1:
            raise ValueError('Expected one table, got %i' % len(tables))

        table_df = tables[0]

        if header:
            table_df.columns = header

        dfs.append(table_df)

    return dfs


def scrape_tables(urls, table_xpath, table_index=0, header=None):
    tables = []

    urls = to_sequence(urls)

    for url in urls:
        tree = url_to_tree(url)

        # select the specified table element
        all_table_els = tree.xpath(table_xpath)
        print 'Got %i elements with xpath %s for url %s' % (len(all_table_els), table_xpath, url)
        table_el = all_table_els[table_index]

        tables.append(table_el)

    return tables


def combine_df_rows(dfs, ignore_index):
    """Take a sequence of DataFrames and append them into one."""
    combined_df = dfs[0]
    for df in dfs[1:]:
        combined_df = combined_df.append(df, ignore_index=ignore_index)

    return combined_df


def paginate_url(pageable_url, pages):
    """Paginate a base url.
    pageable_url: a URL string of the form 'www.foo.com/{pagenum}'
    pages: a sequence of ints, or a single int (pages=3 will yield URLs for pages [1, 2, 3])
    """
    # convenience: make pages a range like [1, 2, 3, ..., N]
    if type(pages) == int:
        pages = range(1, pages+1)

    paged_urls = [pageable_url.format(pagenum=pagenum) for pagenum in pages]
    return paged_urls


if __name__ == "__main__":
# Example
    urls = paginate_url(
        'http://www.boxofficemojo.com/people/?view=Actor&pagenum={pagenum}&sort=sumgross&order=DESC&&p=.htm', 3)

    tables = scrape_tables(urls, '//table//table', table_index=0)

    dfs = df_from_tables(tables,
        header=['rank','actor','total_gross','no_movies','avg_gross','top_picture','top_gross'])

    actor_gross = combine_df_rows(dfs, ignore_index=True)

    print 'Got %i rows from %i pages' % (len(actor_gross), len(urls))
    print actor_gross.head()
