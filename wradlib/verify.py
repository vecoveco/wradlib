#-------------------------------------------------------------------------------
# Name:        verify
# Purpose:
#
# Authors:     Maik Heistermann, Stephan Jacobi and Thomas Pfaff
#
# Created:     26.10.2011
# Copyright:   (c) Maik Heistermann, Stephan Jacobi and Thomas Pfaff 2011
# Licence:     The MIT License
#-------------------------------------------------------------------------------
#!/usr/bin/env python

"""
Verification
^^^^^^^^^^^^

Verification mainly refers to the comparison of radar-based precipitation
estimates to ground truth.

.. autosummary::
   :nosignatures:
   :toctree: generated/

   ErrorMetrics
   PolarNeighbours

"""
# site packages
import numpy as np
from scipy.spatial import KDTree
from scipy import stats
import pylab as pl
from pprint import pprint


# wradlib modules
import wradlib.georef as georef
import wradlib.util as util

class PolarNeighbours():
    """
    For a set of projected point coordinates, extract the neighbouring bin values
    from a data set in polar coordinates. Use as follows:

    First, create an instance of PolarNeighbours by passing all the information needed
    to georeference the polar radar data to the points of interest (see parameters)

    Second, use the method *extract* in order to extract the values from a data array
    which corresponds to the polar coordinates

    Parameters
    ----------
    r : array of floats
        (see georef for documentation)
    az : array of floats
        (see georef for documentation)
    sitecoords : sequence of floats
        (see georef for documentation)
    projstr : string
        (see georef for documentation)
    x : array of floats
        x coordinates of the points in map projection corresponding to projstr
    y : array of floats
        y coordinates of the points in map projection corresponding to projstr
    nnear : int
        number of neighbouring radar bins you would like to find

    """
    def __init__(self, r, az, sitecoords, projstr, x, y, nnear=9):
        self.nnear = nnear
        self.az = az
        self.r = r
        self.x = x
        self.y = y
        # compute the centroid coordinates in lat/lon
        bin_lon, bin_lat = georef.polar2centroids(r, az, sitecoords)
        # project the centroids to cartesian map coordinates
        binx, biny = georef.project(bin_lat, bin_lon, projstr)
        self.binx, self.biny = binx.ravel(), biny.ravel()
        # compute the KDTree
        tree = KDTree(zip(self.binx, self.biny))
        # query the tree for nearest neighbours
        self.dist, self.ix = tree.query(zip(x, y), k=nnear)
    def extract(self, vals):
        """
        Extracts the values from an array of shape (azimuth angles, range gages)
        which correspond to the indices computed during initialisation

        Parameters
        ----------
        vals : array of shape (..., number of azimuth, number of range gates)

        Returns
        -------
        output : array of shape (..., number of points, nnear)

        """
        assert vals.ndim >= 2, \
           'Your <vals> array should at least contain an azimuth and a range dimension.'
        assert tuple(vals.shape[-2:])==(len(self.az), len(self.r)), \
           'The shape of your vals array does not correspond with the range and azimuths you provided for your polar data set'
        shape = vals.shape
        vals = vals.reshape(np.concatenate( (shape[:-2], np.array([len(self.az) * len(self.r)])) ) )
        return vals[...,self.ix]
    def get_bincoords(self):
        """
        Returns all bin coordinates in map projection

        Returns
        -------
        output : array of x coordinates, array of y coordinates

        """
        return self.binx, self.biny
    def get_bincoords_at_points(self):
        """
        Returns bin coordinates only in the neighbourshood of points

        Returns
        -------
        output : array of x coordinates, array of y coordinates

        """
        return self.binx[self.ix], self.biny[self.ix]


class ErrorMetrics():
    """Compute quality metrics from a set of observations (obs) and estimates (est).

    First create an instance of the class using the set of observations and estimates.
    Then compute quality metrics using the class methods. A dictionary of all available
    quality metrics is returned using the *all* method. Method *report* pretty prints
    all these metrics over a scatter plot.

    Parameters
    ----------
    obs: array of floats
        observations (e.g. rain gage observations)
    est: array of floats
        estimates (e.g. radar, adjusted radar, ...)
    minval : float
        threshold value in order to compute metrics only for values larger than minval

    Examples
    --------
    >>> obs = np.random.uniform(0,10,100)
    >>> est = np.random.uniform(0,10,100)
    >>> metrics = ErrorMetrics(obs,est)
    >>> metrics.all()
    >>> metrics.pprint()
    >>> metrics.plot()
    >>> metrics.report()

    """
    def __init__(self, obs, est, minval=None):
        # only remember those entries which have both valid observations AND estimates
        ix = np.intersect1d( util._idvalid(obs, minval=minval),  util._idvalid(est, minval=minval))
        self.obs    = obs[ix]
        self.est    = est[ix]
        self.resids = self.est - self.obs
        self.n      = len(ix)
    def corr(self):
        """Correlation coefficient
        """
        return np.round( np.corrcoef(self.obs, self.est)[0,1], 2)
    def r2(self):
        """Coefficient of determination
        """
        return np.round( ( np.corrcoef(self.obs, self.est)[0,1] )**2, 2)
    def spearman(self):
        """Spearman rank correlation coefficient
        """
        return np.round( stats.stats.spearmanr(self.obs, self.est)[0], 2)
    def nash(self):
        """Nash-Sutcliffe Efficiency
        """
        return 1 - ( self.mse() / np.var(self.obs) )
    def sse(self):
        """Sum of Squared Errors
        """
        return np.round( np.sum( self.resids**2 ), 2)
    def mse(self):
        """Mean Squared Error
        """
        return np.round( self.sse() / self.n, 2)
    def rmse(self):
        """Root Mean Squared Error
        """
        return np.round( self.mse()**0.5, 2)
    def mas(self):
        """Mean Absolute Error
        """
        return np.round( np.mean (np.abs(self.resids) ), 2)
    def meanerr(self):
        """Mean Error
        """
        return np.round( np.mean ( self.resids ) , 2)
    def ratio(self):
        """Mean ratio between observed and estimated
        """
        return np.round( np.mean( self.est / self.obs ), 2)
    def all(self):
        """Returns a dictionary of all error metrics
        """
        out = {}
        out["corr"]     = self.corr()
        out["r2"]       = self.r2()
        out["spearman"] = self.spearman()
        out["nash"]     = self.nash()
        out["sse"]      = self.sse()
        out["mse"]      = self.mse()
        out["rmse"]     = self.rmse()
        out["mas"]      = self.mas()
        out["meanerr"]  = self.meanerr()
        out["ratio"]    = self.ratio()
        return out
    def plot(self, ax=None, unit=""):
        """Scatter plot of estimates vs observations

        Parameters
        ----------
        ax : a matplotlib axes object to plot on
           if None, a new axes object will be created
        unit : string
           measurement unit of the observations / estimates

        """
        doplot = False
        if ax==None:
            fig = pl.figure()
            ax  = fig.add_subplot(111, aspect=1.)
            doplot = True
        ax.plot(self.obs, self.est, "bo")
        maxval = np.max(np.append(self.obs, self.est))
        ax.plot([0,maxval], [0,maxval], "-", color="grey")
        pl.xlabel("Observations (%s)" % unit)
        pl.ylabel("Estimates (%s)" % unit)
        if (not pl.isinteractive()) and doplot:
            pl.show()
        return ax
    def pprint(self):
        """Pretty prints a summary of error metrics
        """
        pprint( self.all() )
    def report(self, metrics=["rmse","r2","meanerr"], ax=None, unit=""):
        """Pretty prints selected error metrics over a scatter plot

        Parameters
        ----------
        metrics : sequence of strings
           names of the metrics which should be included in the report
           defaults to ["rmse","r2","meanerr"]
        ax : a matplotlib axes object to plot on
           if None, a new axes object will be created
        unit : string
           measurement unit of the observations / estimates

        """
        if ax==None:
            fig = pl.figure()
            ax  = fig.add_subplot(111, aspect=1.)
        ax = self.plot(ax=ax, unit=unit)
        xtext = 0.7 * self.obs.max()
        ytext = ( 0.2 + np.arange(0,len(metrics),0.1) )  * self.est.max()
        mymetrics = self.all()
        for i,metric in enumerate(metrics):
            pl.text(xtext, ytext[i], "%s: %s" % (metric,mymetrics[metric]) )
        if not pl.isinteractive():
            pl.show()


if __name__ == '__main__':
    print 'wradlib: Calling module <verify> as main...'




