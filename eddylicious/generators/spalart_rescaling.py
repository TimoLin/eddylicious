import os
import numpy as np
from sys import exit
from scipy.interpolate import interp1d
from scipy.interpolate import interp2d
from ..readers.foamfile_readers import read_u_from_foamfile
from ..writers.tvmfv_writers import write_u_to_tvmfv
from ..writers.hdf5_writers import write_u_to_hdf5

"""Function for generating inlfow velocity fields using
Lund et al's rescaling, but applying the outer profile
througout, see

Lund T.S., Wu X., Squires K.D. Generation of turbulent inflow
data for spatially-developing boundary layer simulations.
J. Comp. Phys.m 140:233-58, 1998.

Spalart, P. R., Strelets, M., & Travin, A. Direct numerical
simulation of large-eddy-break-up devices in a boundary layer.
International Journal of Heat and Fluid Flow, 27(5):902-910,
2006.
"""


def spalart_rescale_mean_velocity(etaPrec, uMeanPrec,
                                  nInfl, etaInfl,
                                  nPointsZInfl,
                                  Ue, U0, gamma):
    """Rescale the mean velocity profile using Lunds rescaling,
    but only using the outer profile.

    This function rescales the mean velocity profile taken from
    the precursor simulation using Lund et al's rescaling,
    however only the outer profile is used.


    Parameters
    ----------
        etaPrec : 1d ndarray
            The values of eta for the corresponding values
            of the mean velocity from the precursor.
        uMeanPrec : 1d ndarray
            The values of the mean velocity from the precursor.
        nInfl : int
            The amount of points in the wall-normal direction
            that contain the boundary layer at the inflow
            boundary. That is, for points beyound nInfl, Ue will
            be prescribed.
        etaInfl : 1d ndarray
            The values of eta for the mesh points at the inflow
            boundary.
            boundary.
        nPointsZInfl : int
            The amount of points in the spanwise direction for
            the inflow boundary.
        Ue : float
            The freestream velocity.
        U0 : float
            The centerline velocity for the precursor.
        gamma : float
            The ration of the friction velocities in the inflow
            boundary layer and the precursor.


    Returns
    -------
        ndarray
            A 2d ndarray with the values of the mean velocity.
            As expected, the values only vary in the y direction.
    """

    uMeanInterp = interp1d(etaPrec, uMeanPrec)
    uMean = gamma*uMeanInterp(etaInfl[0:nInfl]) + Ue - gamma*U0

    uMeanInfl = np.zeros(etaInfl.shape)
    uMeanInfl[0:nInfl] = uMean
    uMeanInfl[nInfl:] = Ue
    uMeanInfl = np.ones((etaInfl.size, nPointsZInfl))*uMeanInfl[:, np.newaxis]
    return uMeanInfl


def spalart_rescale_fluctuations(etaPrec,  pointsZ,
                                 uPrimeX, uPrimeY, uPrimeZ, gamma,
                                 etaInfl, pointsZInfl, nInfl):
    """Rescale the fluctuations of velocity using Lund et al's
    rescaling, but using the outer profile throughout.

    This function rescales the fluctuations of the three
    components of the velocity field taken from the precursor
    simulation using Lund et al's rescaling, but using only
    the outer scales.


    Parameters
    ----------
        etaPrec : ndarray
            The values of eta for the corresponding values
            of the mean velocity from the precursor.
        pointsZ : ndarray
            A 2d array containing the values of z for the points
            of the precuror mesh.
        uPrimeX : ndarray
            A 2d array containing the values of the fluctuations
            of the x component of velocity.
        uPrimeY : ndarray
            A 2d array containing the values of the fluctuations
            of the y component of velocity.
        uPrimeZ : ndarray
            A 2d array containing the values of the fluctuations
            of the z component of velocity.
        gamma : float
            The ration of the friction velocities in the inflow
            boundary layer and the precursor.
        etaInfl : 1d ndarray
            The values of eta for the mesh points at the inflow
            boundary.
        pointsZInfl : int
            A 2d array containing the values of z for the points
            of the inflow boundary.
        nInfl : int
            The amount of points in the wall-normal direction
            that contain the boundary layer at the inflow
            boundary. That is, for points beyound nInfl, 0 will
            be prescribed.


    Returns
    -------
        List of ndarrays
            The list contains three items, each a 2d ndarray.
            The first array contains the rescaled fluctuations of
            the x component of veloicty. The second -- of the y
            component of velocity. The third -- of the z component
            of velocity.
    """

    uPrimeXInfl = np.zeros(pointsZInfl.shape)
    uPrimeYInfl = np.zeros(pointsZInfl.shape)
    uPrimeZInfl = np.zeros(pointsZInfl.shape)

    uPrimeXInterp = interp2d(pointsZ[0, :]/pointsZ[0, -1], etaPrec, uPrimeX)
    uPrimeYInterp = interp2d(pointsZ[0, :]/pointsZ[0, -1], etaPrec, uPrimeY)
    uPrimeZInterp = interp2d(pointsZ[0, :]/pointsZ[0, -1], etaPrec, uPrimeZ)

    uPrimeX = gamma*uPrimeXInterp(pointsZInfl[0, :]/pointsZInfl[0, -1],
                                  etaInfl[0:nInfl])
    uPrimeY = gamma*uPrimeYInterp(pointsZInfl[0, :]/pointsZInfl[0, -1],
                                  etaInfl[0:nInfl])
    uPrimeZ = gamma*uPrimeZInterp(pointsZInfl[0, :]/pointsZInfl[0, -1],
                                       etaInfl[0:nInfl])

    uPrimeXInfl[0:nInfl] = uPrimeX
    uPrimeYInfl[0:nInfl] = uPrimeY
    uPrimeZInfl[0:nInfl] = uPrimeZ 

    return [uPrimeXInfl, uPrimeYInfl, uPrimeZInfl]


def spalart_generate(reader, readPath,
                     writer, writePath,
                     dt, t0, tEnd, timePrecision,
                     uMeanPrec, uMeanInfl,
                     etaPrec, pointsZ,
                     etaInfl, pointsZInfl,
                     nInfl, gamma,
                     yInd, zInd,
                     surfaceName="None", times="None"):
    """Generate the files with the inflow velocity using Lund's rescaling,
    but applying the outer profile througout.

    This function will use Lund et al's rescaling in order to
    generate velocity fields for the inflow boundary.
    The rescaling for the mean profile should be done before-
    hand and is one of the input parameters for this funcion.


    Parameters
    ----------
        reader : str
            The name of the reader which will be used to read the
            velocity field from the precursor simulation.
        readPath : str
            The path for the reader.
        writer: str
            The writer that will be used to save the values of the
            velocity field.
        writePath : str
            The path for the writer
        dt : float
            The time-step to be used in the simulation. This will be
            used to associate a time-value with the produced velocity
            fields.
        t0 : float
            The starting time to be used in the simulation. This will
            be used to associate a time-value with the produced velocity
        timePrecision : int
            Number of points after the decimal to keep for the time value.
        tEnd : float
            The ending time for the simulation.
        uMeanPrec : 1d ndarray
            The values of the mean velocity from the precursor.
        uMeanInfl : 1d ndarray
            The values of the mean velocity for the inflow boundary
            layer.
        etaPrec : ndarray
            The values of eta for the corresponding values
            of the mean velocity from the precursor.
        pointsZ : ndarray
            A 2d array containing the values of z for the points
            of the precuror mesh.
        etaInfl : 1d ndarray
            The values of eta for the mesh points at the inflow
            boundary.
        pointsZInfl : int
            A 2d array containing the values of z for the points
            of the inflow boundary.
        nInfl : int
            The amount of points in the wall-normal direction
            that contain the boundary layer at the inflow
            boundary. That is, for points beyound nInfl, 0 will
            be prescribed.
        gamma : float
            The ration of the friction velocities in the inflow
            boundary layer and the precursor.
        yInd : ndarray
            The sort indices for sorting the read velocity field.
            This is needed when some sorting is performed when the
            mesh points are read and turned into ordered 2d arrays.
            Them the exact same sorting should be applyed to the
            velocity fields.
        zInd : ndarray
            Same as yInd, but for the sorting of the z values.
        surfaceName : str, optional
            For the foamFile reader, the name of the surface used for
            sampling the velocity values.
        times : list of floats, optional
            For the foamFile reader, the times for which the velocity
            field was sampled in the precursor simulation.
    """

    t = t0

    readTimeI = 0
    writeTimeI = 0
    size = int((tEnd-t0)/dt+1)

    while (t <= tEnd):
        print "    Generating for time", t

        # Read U data
        if (reader == "foamFile"):
            [U_X, U_Y, U_Z] = read_u_from_foamfile(
                os.path.join(readPath, times[readTimeI], surfaceName,
                             "vectorField", "U"),
                pointsZ.shape[0], pointsZ.shape[1],
                yInd, zInd)
            readTimeI += 1

            if (readTimeI == len(times)):
                readTimeI = 0
        else:
            print "ERROR. Unknown reader ", reader
            exit()

        # Claculate UPrime
        uPrimeX = U_X - uMeanPrec[:, np.newaxis]
        uPrimeY = U_Y
        uPrimeZ = U_Z

        [uPrimeXInfl, uPrimeYInfl, uPrimeZInfl] = \
            spalart_rescale_fluctuations(
                etaPrec, pointsZ,
                uPrimeX, uPrimeY, uPrimeZ, gamma,
                etaInfl, pointsZInfl,
                nInfl)

        # Combine and flatten
        UInfl_X = np.reshape(uPrimeXInfl+uMeanInfl, (uPrimeXInfl.size, -1),
                             order='F')
        UInfl_Y = np.reshape(uPrimeYInfl, (uPrimeXInfl.size, -1), order='F')
        UInfl_Z = np.reshape(uPrimeZInfl, (uPrimeXInfl.size, -1), order='F')

        UInfl = np.concatenate((UInfl_X, UInfl_Y, UInfl_Z), axis=1)

        if (writer == "tvmfv"):
            write_u_to_tvmfv(writePath, t, UInfl)
        elif (writer == "hdf5"):
            write_u_to_hdf5(writePath, t, UInfl, writeTimeI, size)
        else:
            print "ERROR in lund_generate(). Unknown writer ", writer
            exit()

        writeTimeI += 1
        t += dt
        t = float(("{0:."+str(timePrecision)+"f}").format(t))
