#!/usr/local/bin/python
# encoding: utf-8
"""
Documentation for panstamps can be found here: http://panstamps.readthedocs.org/en/stable

Usage:
    panstamps [options] [--width=<arcminWidth>] [--filters=<filterSet>] [--settings=<pathToSettingsFile>] [--downloadFolder=<path>] (warp|stack) <ra> <dec> [<mjdStart> <mjdEnd>]
    panstamps [options] --closest=<beforeAfter> [--width=<arcminWidth>] [--filters=<filterSet>] [--settings=<pathToSettingsFile>] [--downloadFolder=<path>] <ra> <dec> <mjd>

    -h, --help                              show this help message
    -f, --fits                              download fits (default on)
    -F, --nofits                            don't download fits (default off)
    -j, --jpeg                              download jepg (default off)
    -J, --nojpeg                            don't download jepg (default on)
    -c, --color                             download color jepg (default off)
    -C, --nocolor                           don't download color jepg (default on)
    -a, --annotate                          annotate jpeg (default true)
    -A, --noannotate                        don't annotate jpeg (default false)
    -t, --transient                         add a small red circle at transient location (default false)
    -T, --notransient                       don't add a small red circle at transient location (default true)
    -g, --greyscale                         convert jpeg to greyscale (default false)
    -G, --nogreyscale                       don't convert jpeg to greyscale (default true)
    -i, --invert                            invert jpeg colors (default false)
    -I, --noinvert                          don't invert jpeg colors (default true)
    --width=<arcminWidth>                   width of image in arcsec (default 1)
    --filters=<filterSet>                   filter set to download and use for color image (default gri)
    --downloadFolder=<path>                 path to the download folder, relative or absolute (folder created where command is run if not set)
    --settings=<pathToSettingsFile>         the settings file    
    --closest=<beforeAfter>                 return the warp closest in time to the given mjd. If you want to set a strict time window then pass in a positive or negative time in sec (before | after | secs)

    ra                                      right-ascension in sexagesimal or decimal degrees
    dec                                     declination in sexagesimal or decimal degrees
    mjdStart                                the start of the time-window within which to select images
    mjdEnd                                  the end of the time-window within which to select images
    mjd                                     report the warp closest in time to this mjd
"""
################# GLOBAL IMPORTS ####################
import sys
import os
from os.path import expanduser
os.environ['TERM'] = 'vt100'
import readline
import glob
import pickle
from docopt import docopt, printable_usage
from fundamentals import tools, times
from panstamps.downloader import downloader
from panstamps.image import image
# from ..__init__ import *


def tab_complete(text, state):
    return (glob.glob(text + '*') + [None])[state]


def main(arguments=None):
    """
    *The main function used when ``cl_utils.py`` is run as a single script from the cl, or when installed as a cl command*
    """
    # setup the command-line util settings
    su = tools(
        arguments=arguments,
        docString=__doc__,
        logLevel="WARNING",
        options_first=True,
        projectName="panstamps"
    )
    arguments, settings, log, dbConn = su.setup()

    # unpack remaining cl arguments using `exec` to setup the variable names
    # automatically
    for arg, val in arguments.iteritems():
        if arg[0] == "-":
            varname = arg.replace("-", "") + "Flag"
        else:
            varname = arg.replace("<", "").replace(">", "")
        if isinstance(val, str) or isinstance(val, unicode):
            exec(varname + " = '%s'" % (val,))
        else:
            exec(varname + " = %s" % (val,))
        if arg == "--dbConn":
            dbConn = val
        log.debug('%s = %s' % (varname, val,))

    if ra:
        try:
            ra = float(ra)
        except:
            if ":" not in ra:
                log.error(
                    "ERROR: ra must be in decimal degree or sexagesimal format")
                return

    if dec:
        try:
            dec = float(dec)
        except:
            if ":" not in dec:
                log.error(
                    "ERROR: dec must be in decimal degree or sexagesimal format")
                return

    ## START LOGGING ##
    startTime = times.get_now_sql_datetime()
    log.info(
        '--- STARTING TO RUN THE cl_utils.py AT %s' %
        (startTime,))

    # BUILD KEYWORD DICT
    kwargs = {}
    kwargs["log"] = log
    kwargs["settings"] = settings
    kwargs["ra"] = ra
    kwargs["dec"] = dec

    # FITS OPTIONS
    kwargs["fits"] = True  # DEFAULT
    if fitsFlag == False and nofitsFlag == True:
        kwargs["fits"] = False

    # JPEG OPTIONS
    kwargs["jpeg"] = False  # DEFAULT
    if jpegFlag == True and nojpegFlag == False:
        kwargs["jpeg"] = True

    # COLOR JPEG OPTIONS
    kwargs["color"] = False  # DEFAULT
    if colorFlag == True and nocolorFlag == False:
        kwargs["color"] = True

    # WIDTH OPTION
    kwargs["arcsecSize"] = 60
    if widthFlag:
        kwargs["arcsecSize"] = float(widthFlag) * 60.

    # CHOOSE A FILTERSET
    kwargs["filterSet"] = 'gri'
    if filtersFlag:
        kwargs["filterSet"] = filtersFlag

    for i in kwargs["filterSet"]:
        if i not in "grizy":
            log.error(
                "ERROR: the requested filter must be in the grizy filter set")
            return

    # WHICH IMAGE TYPE TO DOWNLOAD
    if stack:
        kwargs["imageType"] = "stack"
    if warp:
        kwargs["imageType"] = "warp"
    if closestFlag:
        kwargs["imageType"] = "warp"

    # MJD WINDOW
    kwargs["mjdStart"] = mjdStart
    kwargs["mjdEnd"] = mjdEnd
    kwargs["window"] = False

    try:
        kwargs["window"] = int(closestFlag)
    except:
        pass

    if not kwargs["window"]:
        if mjd and closestFlag == "before":
            kwargs["mjdEnd"] = mjd
        elif mjd and closestFlag == "after":
            kwargs["mjdStart"] = mjd
    else:
        if mjd and kwargs["window"] < 0:
            kwargs["mjdEnd"] = mjd
        elif mjd and kwargs["window"] > 0:
            kwargs["mjdStart"] = mjd

    # DOWNLOAD LOCATION
    if downloadFolderFlag:
        home = expanduser("~")
        downloadFolderFlag = downloadFolderFlag.replace("~", home)
    kwargs["downloadDirectory"] = downloadFolderFlag

    # xt-kwarg_key_and_value

    # DOWNLOAD THE IMAGES
    images = downloader(**kwargs)
    fitsPaths, jpegPaths, colorPath = images.get()
    jpegPaths += colorPath

    # POST-DOWNLOAD PROCESS IMAGES
    kwargs = {}
    kwargs["log"] = log
    kwargs["settings"] = settings
    # WIDTH OPTION
    kwargs["arcsecSize"] = 60
    if widthFlag:
        kwargs["arcsecSize"] = float(widthFlag) * 60.

    # ANNOTATE JPEG OPTIONS
    kwargs["crosshairs"] = True  # DEFAULT
    kwargs["scale"] = True
    if annotateFlag == False and noannotateFlag == True:
        kwargs["crosshairs"] = False  # DEFAULT
        kwargs["scale"] = False

    # INVERT OPTIONS
    kwargs["invert"] = False  # DEFAULT
    if invertFlag == True and noinvertFlag == False:
        kwargs["invert"] = True

    # GREYSCALE OPTIONS
    kwargs["greyscale"] = False  # DEFAULT
    if greyscaleFlag == True and nogreyscaleFlag == False:
        kwargs["greyscale"] = True

    # TRANSIENT DOT OPTIONS
    kwargs["transient"] = False  # DEFAULT
    if transientFlag == True and notransientFlag == False:
        kwargs["transient"] = True

    for j in jpegPaths:
        kwargs["imagePath"] = j

        # kwargs["transient"] = False

        # kwargs["invert"] = False
        # kwargs["greyscale"] = False
        oneImage = image(**kwargs)
        oneImage.get()

        # CALL FUNCTIONS/OBJECTS

    if "dbConn" in locals() and dbConn:
        dbConn.commit()
        dbConn.close()
    ## FINISH LOGGING ##
    endTime = times.get_now_sql_datetime()
    runningTime = times.calculate_time_difference(startTime, endTime)
    log.info('-- FINISHED ATTEMPT TO RUN THE cl_utils.py AT %s (RUNTIME: %s) --' %
             (endTime, runningTime, ))

    return


if __name__ == '__main__':
    main()
