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
    return ''.join( chr for chr in string if chr.isalnum() or chr == "_" )

def error(text):
    t = get_template('error.html')
    html = t.render(Context({"errortext": text}))
    return HttpResponse(html)


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
        return scatter(request)
    elif plot_type == "hist":
        return hist(request)
    elif plot_type == "cf":
        return cf(request)

    return error("")


def scatter(request):
    # Parse GET params
    if not "table" in request.GET or not "x" in request.GET or not "y" in request.GET:
        return error("Missing parameters (table, x, and y must all be supplied)")

    table = request.GET['table']
    x_col = request.GET['x']
    y_col = request.GET['y']

    # Read the specified columns from the table
    c = connection.cursor()
    try:
        c.execute("SELECT " + scrub(x_col) + ", " + scrub(y_col) + " FROM " + scrub(table) + " LIMIT 1000")
    except OperationalError:
        return error("Invalid table or column name")
    data = c.fetchall()

    xvals, yvals = zip(*data)

    fig = plt.figure(1)
    fig.clear()
    ax = fig.add_subplot(111)
    plt.scatter(xvals, yvals)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)

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

    # Calculate correlation coefficient
    r = np.corrcoef(xvals, yvals)[1,0]

    t = get_template('scatterplot.html')
    html = t.render(Context({'plot': plot_html, 'r': r}))
    return HttpResponse(html)

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


    t = get_template('histogram.html')
    html = t.render(Context({'plot': plot_html}))
    return HttpResponse(html)

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


    t = get_template('cfplot.html')
    html = t.render(Context({'plot': plot_html}))
    return HttpResponse(html)
