# Ian London 2016
# ianlondon.github.io
#
# A library for extracting HTML elems to pandas dataframes

from lxml import html
from lxml.etree import tostring as html_to_string
import requests
import urlparse

import pandas as pd

import logging
import logging.config


# Set up logging
logger = logging.getLogger(__name__)

fhandler = logging.FileHandler(filename='tablescraper.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fhandler.setFormatter(formatter)
logger.addHandler(fhandler)
logger.setLevel(logging.DEBUG)
# prevent logging bubbling up to iPython Notebook
logger.propagate = False


def to_sequence(x):
    """
    Makes sure an object is a sequence and if it's not, return a 1-tuple containing that object.
    Useful if you want to take an argument which might be one element and might be a list or tuple
    'foo' -> ['foo']
    # other objects like lists, tuples, np.array, dict, etc:
    [1,2,3] -> [1,2,3]
    np.array([1,2,3]) -> np.array([1,2,3])
    {0:42} -> {0:42}
    # etc
    """
    if hasattr(x, '__iter__'):
        return x
    return (x,)

def url_to_tree(url):
    try:
        page = requests.get(url)
    except requests.ConnectionError as e:
        logger.error('Could not connect to url {url}: {e}'.format(url=url,e=e))
        return

    if page.status_code != 200:
        logger.error('{res}: could not get url {url}'.format(res=page.response, url=url))
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


def scrape_multi_elems(keyed_urls, scrape_dict):
    """
    Arguments:
        url_label: a dict containing URL strings keyed by your url labels, eg:
            {'banana':'http://www.fruits.com/banana', 'orange':'http://www.fruits.com/orange'}

        scrape_dict: a dict containing xpaths keyed by your element labels. eg:
            {'calories':'xpath_selector1', 'fiber':'xpath_selector2', ...}

    Returns:
        final_results: a dict of dicts. The first key corresponds to the url label
        and the second key corresponds to the element label.

        Example -- from the banana page, get the 0th 'calories' element:
            final_results['banana']['calories'][0]

    Example:
        >>> scrape_multi_elems({'examp':'http://www.example.com'},{'txt':'//h1/text()','p':'//p/text()'})
        {'examp': {'p': ['This domain is established to be used for illustrative examples in documents. \
        You may use this\n    domain in examples without prior coordination or asking for permission.'],
        'txt': ['Example Domain']}}

    """
    final_results = {}
    page_results = {}

    logger.info('Beginning new multi-scrape of %i urls' % len(keyed_urls))

    for url_label, url in keyed_urls.iteritems():
        tree = url_to_tree(url)

        for el_label, xpath in scrape_dict.iteritems():
            all_elems = tree.xpath(xpath)
            logger.info('multiscrape got %i elements with xpath %s for url %s' % (len(all_elems), xpath, url))

            page_results[el_label] = all_elems

        final_results[url_label] = page_results

    return final_results

def scrape_elems(urls, elem_xpath, elem_index=0, fail_val=None):
    final_elems = []

    urls = to_sequence(urls)

    logger.info('Beginning new scrape of %i urls' % len(urls))

    for url in urls:
        tree = url_to_tree(url)

        # select the specified elem element
        all_elems = tree.xpath(elem_xpath)
        logger.info('Got %i elements with xpath %s for url %s' % (len(all_elems), elem_xpath, url))

        if elem_index is not None:
            try:
                logger.info('selected the %ith' % elem_index)
                elem_el = all_elems[elem_index]
            except IndexError:
                logger.warn('element index out of range, falling back to fail_val')
                elem_el = fail_val

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

def url_params(url):
    """
    Shorthand to get parameters from a URL
    >>> url_params('http://www.boxofficemojo.com/people/chart/?view=Actor&id=paulbettany.htm')
    {'id': ['paulbettany.htm'], 'view': ['Actor']}
    Watch out, the parameters are often a 1-element list.
    """
    return urlparse.parse_qs(urlparse.urlparse(url).query)

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
