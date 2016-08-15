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
import time
import StringIO
import sys

SCHEMA = json.loads(open(os.path.dirname(os.path.abspath(__file__)) + "/schema.json").read())

# Helper functions

def scrub(string):
    return ''.join( chr for chr in string.strip() if chr.isalnum() or chr in "_-<>., " )

def getfilter(request):
    _filter = ""
    if "filter" in request.GET:
        _filter = request.GET['filter']
    return _filter

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
        for part in filtertext.split(",,"):
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

def parse_table(text):
    # Do inner joins!
    parts = text.split(",")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        if parts[0] == "atlasgal_full_csc_16oct14" and parts[1] == "cal_vlsr_distances":
            return "atlasgal_full_csc_16oct14 INNER JOIN cal_vlsr_distances on atlas_name = csc_name"
    return text

def coolfilename(_format):
    return "ATLASGAL-" + str(int(time.time())) + "." + _format

def get_data(request): # TODO make this work for not just scatter plots!!
    # Parse GET params
    if not "table" in request.GET or not "cols" in request.GET:
        raise Exception("Missing parameters (table, x, and y must all be supplied)")

    table = request.GET['table']
    cols = request.GET['cols']

    if "filter" in request.GET:
        _filter = parse_filter(request.GET['filter'])
    else:
        _filter = ""

    if "colours" in request.GET:
        if request.GET['colours']:
            colourcol = ", " + scrub(request.GET['colours'])
        else:
            colourcol = ""
    else:
        colourcol = ""

    query = "SELECT " + scrub(cols) + colourcol + " FROM " + parse_table(scrub(table)) + " " + _filter

    sys.stdout.write(query)

    # Read the specified columns from the table
    c = connection.cursor()
    c.execute(query)
    data = c.fetchall()
    filtered_data = []
    for datum in data:
        if not (-999 in datum or None in datum):
            filtered_data.append(datum)
    return filtered_data

def get_columns(table):
    c = connection.cursor()
    c.execute("SELECT * FROM " + scrub(table) + " LIMIT 1")
    col_titles = [description[0] for description in c.description]
    return col_titles

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

    _filter = ""
    filtertext = ""
    if "filter" in request.GET:
        filtertext = request.GET['filter']
        _filter = parse_filter(request.GET['filter'])

    c = connection.cursor()
    try:
        c.execute("SELECT * FROM " + parse_table(table) + " " + _filter + " LIMIT 100")
    except Exception, e:
        return error(str(e))
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
    c.execute("SELECT title FROM tables WHERE name = ?", (table.split(",")[0],))
    title = c.fetchone()
    if not title:
        title = table
    else:
        title = title[0]

    t = get_template('showtable.html')
    if filtertext == "":
        filters = None
    else:
        filters = [parse_filter(filtertext)]
    html = t.render(Context({"rows": rows, "coltitles": new_col_titles, "tablename": table, "tabletitle": title, "filter": filtertext, "filters": filters}))

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

def random_colour():
    return random.random()

def scatter_page(request):
    try:
        data = get_data(request)
    except Exception, e:
        return error(str(e))

    if len(data) == 0:
        return error("No data matched those criteria!")

    xvals, yvals = zip(*data)[0:2]
    r = np.corrcoef(xvals, yvals)[1,0]

    plot_url = "../plot/" + request.get_full_path().split("/")[-1]

    table = request.GET['table']
    all_cols = get_columns(table)
    x, y = request.GET['cols'].split(",")

    c = Context({"ploturl": plot_url, "r": r, "cols": request.GET['cols'], "table": request.GET['table'], "filter": getfilter(request),
        "x": x, "y": y, "table": table, "all_cols": all_cols})
    return HttpResponse(get_template("scatterplot.html").render(c))

def cf_page(request):
    plot_url = "../plot/" + request.get_full_path().split("/")[-1]
    return HttpResponse(get_template("cfplot.html").render(Context({"ploturl": plot_url})))
def hist_page(request):
    plot_url = "../plot/" + request.get_full_path().split("/")[-1]
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
    interactive = False

    c = connection.cursor()
    data = get_data(request)

    xvals, yvals = zip(*data)[0:2]

    table = request.GET['table']
    x_col, y_col = scrub(request.GET['cols']).split(",")

    fig = plt.figure(1)
    fig.clear()
    ax = fig.add_subplot(111)

    if "xlabel" in request.GET:
        ax.set_xlabel(request.GET['xlabel'])
    else:
        ax.set_xlabel(x_col)
    if "ylabel" in request.GET:
        ax.set_ylabel(request.GET['ylabel'])
    else:
        ax.set_ylabel(y_col)

    if "scale" in request.GET:
        ax.set_xscale(request.GET['scale'])
        ax.set_yscale(request.GET['scale'])
        if request.GET['scale'] != "linear":
            interactive = False

    if "colours" in request.GET:
        if request.GET['colours'] != "":
            used_colours = {}
            colours = zip(*data)[2]
            if isinstance(colours[0], str) or isinstance(colours[0], unicode):
                c_array = []
                for c in colours:
                    if c in used_colours:
                        c_array.append(used_colours[c])
                    else:
                        used_colours[c] = random_colour()
                        c_array.append(used_colours[c])
                plt.scatter(xvals, yvals, c=c_array, s=100, cmap=matplotlib.cm.viridis)
                plt.legend(handles = [matplotlib.patches.Patch(color=matplotlib.cm.viridis(v), label=k) for k,v in used_colours.iteritems()])
            else:
                c_array = colours
                sc = plt.scatter(xvals, yvals, c=c_array, s=100)
                plt.colorbar(sc)
        else:
            plt.scatter(xvals,yvals)

    else:
        plt.scatter(xvals, yvals)

    if "title" in request.GET:
        if request.GET['title']:
            plt.title(request.GET['title'])

    if "fitline" in request.GET:
        # Set axis scales back to linear, FOR NOW
        ax.set_xscale("linear")
        ax.set_yscale("linear")
        
        if request.GET['fitline'] == "linear":
            # Fit a line to the points
            def f(x, a, b):
                # Straight line
                return a*x + b

            popt, pcov = curve_fit(f, xvals, yvals)
            optf = lambda x: f(x, popt[0], popt[1])
            plt.plot([min(xvals), max(xvals)], [optf(min(xvals)), optf(max(xvals))], 'r-')

    if "download" in request.GET:
        # Prepare the plot for download
        _format = request.GET['download']
        outfile = StringIO.StringIO()
        plt.savefig(outfile, format=_format)
        response = HttpResponse(outfile.getvalue(), content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(coolfilename(_format))
        return response
    elif interactive:
        plot_html = mpld3.fig_to_html(fig)
        return HttpResponse(plot_html)
    else:
        outfile = StringIO.StringIO()
        plt.savefig(outfile, format="PNG", figsize=(8, 6), dpi=80)
        return HttpResponse(outfile.getvalue(), content_type="image/png")

def hist(request):
    nbins = 10
    if "nbins" in request.GET:
        if type(eval(request.GET['nbins'])) == int:
            nbins = int(request.GET['nbins'])

    try:
        data = get_data(request)
    except Exception, e:
        return error(str(e))

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
