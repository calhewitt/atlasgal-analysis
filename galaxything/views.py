import matplotlib
matplotlib.use('Agg') # Stop MPL trying to open windows - will cause errors when no WM is running!

from django.http import HttpResponse
import matplotlib.pyplot as plt
import mpld3
from django.template.loader import get_template
from django.template import Context
from django.db import connection, OperationalError
from scipy.optimize import curve_fit
import numpy as np
import os
import json
import random

SCHEMA = json.loads(open(os.path.dirname(os.path.abspath(__file__)) + "/schema.json").read())

# Helper functions

def scrub(string):
    return ''.join( chr for chr in string.strip() if chr.isalnum() or chr in "_-<>. " )

def error(text):
    t = get_template('error.html')
    html = t.render(Context({"errortext": text}))
    return HttpResponse(html)

def fromwords(symbol):
    symbol = symbol.upper()
    if symbol == "GT":
        return ">"
    elif symbol == "LT":
        return "<"
    elif symbol == "BETWEEN":
        return "BETWEEN"
    else:
        raise

def parse_filter(filtertext):
    try:
        result = "WHERE "
        for part in filtertext.split(";"):
            terms = part.split(",")
            result += (terms[0] + " ")
            result += (fromwords(terms[1]) + " ")
            result += terms[2]
            for term in terms[3:]:
                result += " AND "
                result += term
            result += " AND "
        return scrub(result[:-4])
    except:
        return ""


def get_data(request): # TODO make this work for not just scatter plots!!
    # Parse GET params
    if not "table" in request.GET or not "x" in request.GET or not "y" in request.GET:
        raise Exception("Missing parameters (table, x, and y must all be supplied)")

    table = request.GET['table']
    x_col = request.GET['x']
    y_col = request.GET['y']

    if "filter" in request.GET:
        _filter = parse_filter(request.GET['filter'])
    else:
        _filter = ""

    # Read the specified columns from the table
    c = connection.cursor()
    c.execute("SELECT " + scrub(x_col) + ", " + scrub(y_col) + " FROM " + scrub(table) + " " + _filter + " LIMIT 1000")
    data = c.fetchall()
    filtered_data = []
    for datum in data:
        if not -999 in datum:
            filtered_data.append(datum)
    return filtered_data

# Live views

def picktable(request):
    c = connection.cursor()
    c.execute("SELECT * FROM tables")
    tables = c.fetchall()
    t = get_template("picktable.html")
    html = t.render(Context({"tables": tables}))
    return HttpResponse(html)

def showtable(request):
    if not "table" in request.GET:
        return error("Table parameter not supplied")

    table = scrub(request.GET['table'])

    c = connection.cursor()
    try:
        c.execute("SELECT * FROM " + table + " LIMIT 1000")
    except OperationalError:
        return error("Bad table name")
    rows = c.fetchall()
    col_titles = [description[0] for description in c.description]
    new_col_titles = []
    for title in col_titles:
        title = title.strip() # That pesky whitespace
        if title in SCHEMA["columns"]:
            new_title, unit, plottable = SCHEMA["columns"][title]
            new_col_titles.append({"name": new_title, "oname": title, "unit": unit, "plottable": plottable})
        else:
            if title == "x": title = "_x"
            if title == "y": title = "_y"
            new_col_titles.append({"name": title, "oname": title, "unit": None, "plottable:": False})

    # Find the proper title given to the table
    c.execute("SELECT title FROM tables WHERE name = ?", (table,))
    title = c.fetchone()
    if not title:
        title = table
    else:
        title = title[0]

    t = get_template('showtable.html')
    html = t.render(Context({"rows": rows, "coltitles": new_col_titles, "tablename": table, "tabletitle": title}))

    return HttpResponse(html)


def showplot(request):
    # TODO support different plot types

    plot_type = "scatter"
    if "type" in request.GET:
        plot_type = request.GET['type']
    if not plot_type in ["scatter", "hist", "cf"]:
        return error("Invalid plot type")

    if plot_type == "scatter":
        return scatter_page(request)
    elif plot_type == "hist":
        return hist_page(request)
    elif plot_type == "cf":
        return cf_page(request)

    return error("")

def scatter_page(request):
    try:
        data = get_data(request)
    except Exception, e:
        return error(str(e))

    if len(data) == 0:
        return error("No data matched those criteria!")

    xvals, yvals = zip(*data)
    r = np.corrcoef(xvals, yvals)[1,0]

    _filter = ""
    if "filter" in request.GET:
        _filter = request.GET['filter']

    plot_url = "../plot/?type=scatter&x=" + request.GET['x'] + "&y=" + request.GET['y'] + "&table=" + request.GET['table'] + "&filter=" + _filter
    c = Context({"ploturl": plot_url, "r": r, "x": request.GET['x'], "y": request.GET['y'], "table": request.GET['table']})
    return HttpResponse(get_template("scatterplot.html").render(c))

def cf_page(request):
    plot_url = "../plot/?type=cf&col=" + request.GET['col'] + "&table=" + request.GET['table']
    return HttpResponse(get_template("cfplot.html").render(Context({"ploturl": plot_url})))
def hist_page(request):
    plot_url = "../plot/?type=hist&col=" + request.GET['col'] + "&table=" + request.GET['table']
    return HttpResponse(get_template("histogram.html").render(Context({"ploturl": plot_url})))

def plot(request):
    # TODO support different plot types

    plot_type = "scatter"
    if "type" in request.GET:
        plot_type = request.GET['type']
    if not plot_type in ["scatter", "hist", "cf"]:
        return error("Invalid plot type")

    if plot_type == "scatter":
        return scatter(request)
    elif plot_type == "hist":
        return hist(request)
    elif plot_type == "cf":
        return cf(request)

    return error("")


def scatter(request):
    data = get_data(request)

    xvals, yvals = zip(*data)

    table = request.GET['table']
    x_col = request.GET['x']
    y_col = request.GET['y']

    fig = plt.figure(1)
    fig.clear()
    ax = fig.add_subplot(111)
    plt.scatter(xvals, yvals)
    if "xlabel" in request.GET:
        ax.set_xlabel(request.GET['xlabel'])
    else:
        ax.set_xlabel(x_col)
    if "ylabel" in request.GET:
        ax.set_ylabel(request.GET['ylabel'])
    else:
        ax.set_ylabel(y_col)

    if "xscale" in request.GET:
        ax.set_xscale(request.GET['xscale'])
    if "yscale" in request.GET:
        ax.set_yscale(request.GET['yscale'])

    # Fit a line to the points

    def f(x, a, b):
        # Straight line
        return a*x + b

    popt, pcov = curve_fit(f, xvals, yvals)
    optf = lambda x: f(x, popt[0], popt[1])
    plt.plot([min(xvals), max(xvals)], [optf(min(xvals)), optf(max(xvals))], 'r-')

    #ax.set_xlabel(request.GET['xlabel'])
    #ax.set_ylabel(request.GET['ylabel'])

    plot_html = mpld3.fig_to_html(fig)

    return HttpResponse(plot_html)

def hist(request):
    # Parse GET params
    if not "table" in request.GET or not "col" in request.GET :
        return error("Missing parameters (table and col must both be supplied)")

    nbins = 10
    if "nbins" in request.GET:
        if type(eval(request.GET['nbins'])) == int:
            nbins = int(request.GET['nbins'])

    table = request.GET['table']
    col = request.GET['col']

    # Read the specified columns from the table
    c = connection.cursor()
    try:
        c.execute("SELECT " + scrub(col) + " FROM " + scrub(table))
    except OperationalError:
        return error("Invalid table or column name")
    data = c.fetchall()

    xvals = zip(*data)[0]

    fig = plt.figure(1)
    fig.clear()
    ax = fig.add_subplot(111)
    plt.hist(xvals, nbins)

    plot_html = mpld3.fig_to_html(fig)

    return HttpResponse(plot_html)

def cf(request):
    # Parse GET params
    if not "table" in request.GET or not "col" in request.GET :
        return error("Missing parameters (table and col must both be supplied)")

    table = request.GET['table']
    col = request.GET['col']

    # Read the specified columns from the table
    c = connection.cursor()
    try:
        c.execute("SELECT " + scrub(col) + " FROM " + scrub(table))
    except OperationalError:
        return error("Invalid table or column name")
    data = c.fetchall()

    xvals = zip(*data)[0]

    fig = plt.figure(1)
    fig.clear()
    ax = fig.add_subplot(111)
    n,bins,patches = plt.hist(xvals, 100, histtype='step', cumulative=True)
    patches[0].set_xy(patches[0].get_xy()[:-1])

    plot_html = mpld3.fig_to_html(fig)

    return HttpResponse(plot_html)
