# Ian London 2016
# ianlondon.github.io
#
# A library for extracting HTML elems to pandas dataframes

from lxml import html
from lxml.etree import tostring as html_to_string
import requests
import pandas as pd

def to_sequence(x):
    """
    Makes sure an object is a sequence and if it's not, return a 1-tuple containing that object.
    Useful if you want to take an argument which might be one element and might be a list or tuple
    """
    if isinstance(x, list) or isinstance(x, tuple):
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


def dfs_from_tables(table_els, header=None, skiprows=1):
    """
    From a single lxml.html.Htmltableent <table> or a sequence of them,
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


def scrape_elems(urls, elem_xpath, elem_index=0, header=None):
    final_elems = []

    urls = to_sequence(urls)

    for url in urls:
        tree = url_to_tree(url)

        # select the specified elem element
        all_elems = tree.xpath(elem_xpath)
        print 'Got %i elements with xpath %s for url %s' % (len(all_elems), elem_xpath, url)

        if elem_index is not None:
            print 'selected the %ith' % elem_index
            elem_el = all_elems[elem_index]

        final_elems.append(elem_el)

    return final_elems


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

    elems = scrape_elems(urls, '//elem//elem', elem_index=0)

    dfs = dfs_from_elems(elems,
        header=['rank','actor','total_gross','no_movies','avg_gross','top_picture','top_gross'])

    actor_gross = combine_df_rows(dfs, ignore_index=True)

    print 'Got %i rows from %i pages' % (len(actor_gross), len(urls))
    print actor_gross.head()
