"""@package docstring

ExaDiS python utilities

Implements utility functions for the ExaDiS python binding

* insert_frank_read_src()
* insert_infinite_line()
* generate_line_config()

* get_segments_length()
* dislocation_density()
* dislocation_charge()

* read_paradis()
* write_data()
* write_vtk()

Nicolas Bertin
bertin1@llnl.gov
"""

import numpy as np
import pyexadis
from pyexadis_base import NodeConstraints, ExaDisNet
try:
    # Try importing DisNetManager from OpenDiS
    from framework.disnet_manager import DisNetManager
except ImportError:
    # Use dummy DisNetManager if OpenDiS is not available
    from pyexadis_base import DisNetManager


def insert_frank_read_src(cell, nodes, segs, burg, plane, length, center, theta=0.0, linedir=None, numnodes=10):
    """Insert a Frank-Read source into the list of nodes and segments
    cell: network cell
    nodes: list of nodes
    segs: list of segments
    burg: Burgers vector of the source
    plane: habit plane normal of the source
    theta: character angle of the source in degrees
    linedir: line direction of the source
    length: length of the source
    center: center position of the source
    numnodes: number of discretization nodes for the source
    """
    plane = plane / np.linalg.norm(plane)
    if np.abs(np.dot(burg, plane)) >= 1e-5:
        print('Warning: Burgers vector and plane normal are not orthogonal')
    
    if not linedir is None:
        ldir = np.array(linedir)
        ldir = ldir / np.linalg.norm(ldir)
    else:
        b = burg / np.linalg.norm(burg)
        y = np.cross(plane, b)
        y = y / np.linalg.norm(y)
        ldir = np.cos(theta*np.pi/180.0)*b+np.sin(theta*np.pi/180.0)*y
    
    istart = len(nodes)
    for i in range(numnodes):
        p = center -0.5*length*ldir + i*length/(numnodes-1)*ldir
        constraint = NodeConstraints.PINNED_NODE if (i == 0 or i == numnodes-1) else NodeConstraints.UNCONSTRAINED
        nodes.append(np.concatenate((p, [constraint])))
    
    for i in range(numnodes-1):
        segs.append(np.concatenate(([istart+i, istart+i+1], burg, plane)))
    
    return nodes, segs


def insert_infinite_line(cell, nodes, segs, burg, plane, origin, theta=0.0, linedir=None, maxseg=-1, trial=False):
    """Insert an infinite line into the list of nodes and segments
    cell: network cell
    nodes: list of nodes
    segs: list of segments
    burg: Burgers vector of the line
    plane: habit plane normal of the source
    origin: origin position of the line
    theta: character angle of the line in degrees
    linedir: line direction
    maxseg: maximum discretization length of the line
    trial: do a trial insertion only (to test if insertion is possible)
    """
    plane = plane / np.linalg.norm(plane)
    if np.abs(np.dot(burg, plane)) >= 1e-5:
        print('Warning: Burgers vector and plane normal are not orthogonal')
    
    if not linedir is None:
        ldir = np.array(linedir)
        ldir = ldir / np.linalg.norm(ldir)
    else:
        b = burg / np.linalg.norm(burg)
        y = np.cross(plane, b)
        y = y / np.linalg.norm(y)
        ldir = np.cos(theta*np.pi/180.0)*b+np.sin(theta*np.pi/180.0)*y

    h = np.array(cell.h)
    Lmin = np.min(np.linalg.norm(h, axis=1))
    seglength = 0.15*Lmin
    
    if maxseg > 0:
        seglength = np.min([seglength, maxseg])

    length = 0.0
    meet = 0
    maxnodes = 1000
    numnodes = 0
    p = 1.0*origin
    originpbc = 1.0*origin
    while ((~meet) & (numnodes < maxnodes)):
        p += seglength*ldir
        pp = np.asarray(cell.closest_image(Rref=origin, R=p))
        dist = np.linalg.norm(pp-origin)
        if ((numnodes > 0) & (dist < seglength)):
            originpbc = np.asarray(cell.closest_image(Rref=p, R=origin))
            meet = 1
        numnodes += 1

    if numnodes == maxnodes:
        if trial:
            return -1.0
        else:
            print('Warning: infinite line is too long, aborting')
            return nodes, segs

    if trial:
        return np.linalg.norm(originpbc-origin)
    else:
        istart = len(nodes)
        for i in range(numnodes):
            p = origin + 1.0*i/numnodes*(originpbc-origin)
            constraint = NodeConstraints.UNCONSTRAINED
            nodes.append(np.concatenate((p, [constraint])))
        for i in range(numnodes):
            segs.append(np.concatenate(([istart+i, istart+(i+1)%numnodes], burg, plane)))
        return nodes, segs


def generate_line_config(crystal, Lbox, num_lines, theta=None, maxseg=-1, seed=-1, verbose=True):
    """Generate a configuration made of straight, infinite dislocation lines
    * Dislocation lines are generated by cycling through the list of signed
      slip systems (+/- Burgers vectors). I.e., for a balanced configuration 
      (neutral Burgers charge), it is advised to use a number of dislocation lines 
      as a multiple of 24 (=12*2), so that dislocation dipoles are created.
    * If a list of character angles (theta) is provided, each dislocation will be
      randomly assigned one of the character angles from the list. If not provided,
      the character angles will be chosen such that the dislocation density is
      roughly equal between all slip systems.
    Arguments:
    * crystal: crystal structure
    * Lbox: box size
    * num_lines: number of dislocation lines
    * theta: list of possible character angles in degrees
    * maxseg: maximum discretization length of the line
    * verbose: print information
    """    
    if verbose: print('generate_line_config()')
    
    if crystal in ['BCC', 'bcc']:
        # Define the 12 <111>{110} slip systems
        b = np.array([
            [-1.,1.,1.], [1.,1.,1.], [-1.,-1.,1.], [1.,-1.,1.],
            [-1.,1.,1.], [1.,1.,1.], [-1.,-1.,1.], [1.,-1.,1.],
            [-1.,1.,1.], [1.,1.,1.], [-1.,-1.,1.], [1.,-1.,1.]
        ])
        n = np.array([
            [0.,-1.,1.], [0.,-1.,1.], [0.,1.,1.], [0.,1.,1.],
            [1.,0.,1.], [-1.,0.,1.], [1.,0.,1.], [-1.,0.,1.],
            [1.,1.,0.], [-1.,1.,0.], [-1.,1.,0.], [1.,1.,0.]
        ])
        
    elif crystal in ['FCC', 'fcc']:
        # Define the 12 <110>{111} slip systems
        b = np.array([
            [0.,1.,-1.], [1.,0.,-1.], [1.,-1.,0.],
            [0.,1.,-1.], [1.,0.,1.], [1.,1.,0.],
            [0.,1.,1.], [1.,0.,-1.], [1.,1.,0.],
            [0.,1.,1.], [1.,0.,1.], [1.,-1.,0.]
        ])
        n = np.array([
            [1.,1.,1.], [1.,1.,1.], [1.,1.,1.],
            [-1.,1.,1.], [-1.,1.,1.], [-1.,1.,1.],
            [1.,-1.,1.], [1.,-1.,1.], [1.,-1.,1.],
            [1.,1.,-1.], [1.,1.,-1.], [1.,1.,-1.]
        ])
        
    else:
        raise ValueError('Error: unknown crystal type = %s' % crystal)
    
    nsys = b.shape[0]
    b = b / np.linalg.norm(b, axis=1)[:,None]
    n = n / np.linalg.norm(n, axis=1)[:,None]
    cell = pyexadis.Cell(Lbox)
    
    if theta is None:
        # Determine the character angles of each dipole
        # such that the densities among slip systems are close.
        # We need to do this because the line length of each dipole
        # depends on the crystal orientation and slip system,
        # with each of which likely to have a different periodicity.
        # Here we first determine the dipole with maximum length.
        ntheta = 19
        theta = 90.0/(ntheta-1)*np.arange(ntheta)
        theta_minlength = np.zeros((nsys, ntheta))
        for isys in range(nsys):
            burg, plane = b[isys], n[isys]
            c = np.array(cell.center())
            # Find character angle that minimizes the line length
            minlength = 1e20
            for t in range(ntheta):
                nodes, segs = [], []
                length = insert_infinite_line(cell, nodes, segs, burg, plane, c,
                                              theta=theta[t], maxseg=maxseg, trial=True)
                theta_minlength[isys,t] = length
        
        # Maximum dipole size among all slip systems
        theta_minlength = np.ma.masked_less(theta_minlength, 0.0)
        minlength = theta_minlength.min(axis=1).filled(-1.0)
        maxlength = np.max(minlength)
        if maxlength > 10*Lbox or np.min(minlength) < 0.0:
            raise ValueError('Error: cannot find appropriate line to insert')
        
        # Select character angle for the slip system that is
        # the closest to the maximum dipole length across/
        # all the slip systems
        theta_sys = np.argmin(np.abs(theta_minlength-maxlength), axis=1)
        theta_sys = theta[theta_sys][:,None]
    else:
        theta_sys = np.tile(np.array(theta), (nsys, 1))
    
    # Insert the lines
    if seed > 0: np.random.seed(seed)
    pos = np.random.rand(num_lines, 3)
    pos = np.array(cell.origin) + np.matmul(pos, np.array(cell.h).T)
    ithe = np.random.randint(0, theta_sys.shape[1], num_lines)
    nodes, segs = [], []
    
    for i in range(num_lines):
        isys = i % nsys
        burg, plane = b[isys], n[isys]
        
        idip = np.floor(i/nsys).astype(int) % 2 # alternate sign to create dipoles
        lsign = 1-2*idip
        
        edir = np.cross(plane, burg)
        edir = edir / np.linalg.norm(edir)
        theta = theta_sys[isys,ithe[i-idip*nsys]]
        ldir = np.cos(theta*np.pi/180.0)*burg + np.sin(theta*np.pi/180.0)*edir
        
        nodes, segs = insert_infinite_line(cell, nodes, segs, burg, plane, pos[i],
                                           linedir=lsign*ldir, maxseg=maxseg)       
        if verbose: print(' insert dislocation: b = %.3f %.3f %.3f, n = %.3f %.3f %.3f, theta = %.1f deg' % (*burg, *plane, theta))
    
    G = ExaDisNet(cell, nodes, segs)
    return G


def get_segments_length(N: DisNetManager) -> np.ndarray:
    """ Returns the list of dislocation segment lenghts of the network
    """
    data = N.export_data()
    # cell
    cell = data.get("cell")
    cell = pyexadis.Cell(h=cell.get("h"), origin=cell.get("origin"), is_periodic=cell.get("is_periodic"))
    # nodes
    nodes = data.get("nodes")
    rn = nodes.get("positions")
    # segments
    segs = data.get("segs")
    segsnid = segs.get("nodeids")
    r1 = np.array(cell.closest_image(Rref=np.array(cell.center()), R=rn[segsnid[:,0]]))
    r2 = np.array(cell.closest_image(Rref=r1, R=rn[segsnid[:,1]]))
    Lseg = np.linalg.norm(r2-r1, axis=1)
    return Lseg


def dislocation_density(N: DisNetManager, burgmag: float) -> float:
    """ Returns the dislocation density of the network
    """
    len = get_segments_length(N).sum()
    vol = np.abs(np.linalg.det(N.export_data().get("cell")["h"]))
    rho = len/vol/burgmag**2
    return rho


def dislocation_charge(N: DisNetManager) -> np.ndarray:
    """ Returns the dislocation charge (net Nye's tensor) of the network
    """
    data = N.export_data()
    cell = data.get("cell")
    cell = pyexadis.Cell(h=cell.get("h"), origin=cell.get("origin"), is_periodic=cell.get("is_periodic"))
    # nodes
    nodes = data.get("nodes")
    rn = nodes.get("positions")
    # segments
    segs = data.get("segs")
    segsnid = segs.get("nodeids")
    r1 = np.array(cell.closest_image(Rref=np.array(cell.center()), R=rn[segsnid[:,0]]))
    r2 = np.array(cell.closest_image(Rref=r1, R=rn[segsnid[:,1]]))
    t = r2-r1
    b = segs.get("burgers")
    alpha = np.einsum('ij,ik->jk', b, t)
    return alpha


def read_paradis(datafile: str) -> DisNetManager:
    """ Read dislocation network in ParaDiS format
    """
    G = ExaDisNet()
    G.read_paradis(datafile)
    return DisNetManager(G)


def write_data(N: DisNetManager, datafile: str):
    """ Write dislocation network in ParaDiS format
    """
    N.get_disnet(ExaDisNet).write_data(datafile)


def write_vtk(N: DisNetManager, vtkfile: str, segprops={}, pbc_wrap=True):
    """ Write dislocation network in vtk format
    """
    data = N.export_data()
    # cell
    cell = data.get("cell")
    cell = pyexadis.Cell(h=cell.get("h"), origin=cell.get("origin"), is_periodic=cell.get("is_periodic"))
    cell_origin, cell_center, h = np.array(cell.origin), np.array(cell.center()), np.array(cell.h)
    c = cell_origin + np.array([np.zeros(3), h[0], h[1], h[2], h[0]+h[1],
                                h[0]+h[2], h[1]+h[2], h[0]+h[1]+h[2]])
    # nodes
    nodes = data.get("nodes")
    rn = nodes.get("positions")
    # segments
    segs = data.get("segs")
    segsnid = segs.get("nodeids")
    r1 = np.array(cell.closest_image(Rref=np.array(cell.center()), R=rn[segsnid[:,0]]))
    r2 = np.array(cell.closest_image(Rref=r1, R=rn[segsnid[:,1]]))
    b = segs.get("burgers")
    p = segs.get("planes")
    
    # PBC wrapping
    if pbc_wrap:
        
        eps = 1e-10
        hinv = np.linalg.inv(h)
        def outside_box(p):
            s = np.matmul(hinv, p - cell_origin)
            return np.any(s < -eps) or np.any(s > 1.0+eps)
        
        def facet_intersection_position(r1, r2, i):
            s1 = np.matmul(hinv, r1 - cell_origin)
            s2 = np.matmul(hinv, r2 - cell_origin)
            t = s2 - s1
            t0 = -(s1 - 0.0) / (t + eps)
            t1 = -(s1 - 1.0) / (t + eps)
            s = np.hstack((t0, t1))
            s[s < eps] = 1.0
            facet = np.argmin(s)
            if s[facet] < 1.0:
                pos = np.matmul(h, s1 + s[facet]*t) + cell_origin
                sfacet = s[facet]
            else:
                facet = -1
                pos = r2
                sfacet = 1.0
            return pos, facet, sfacet
            
        segsid = []
        rsegs = []
        for i in range(segsnid.shape[0]):
            n1, n2 = segsnid[i]
            r1 = np.array(cell.closest_image(Rref=cell_center, R=rn[n1]))
            r2 = np.array(cell.closest_image(Rref=r1, R=rn[n2]))
            out = outside_box(r2)
            while out:
                pos, facet, sfacet = facet_intersection_position(r1, r2, i)
                if facet < 0: break
                segsid.append(i)
                rsegs.append([r1, pos])
                r1 = pos + (1-2*np.floor(facet/3)) * (1.0-2*eps)*h[:,facet%3]
                r2 = np.array(cell.closest_image(Rref=r1, R=rn[n2]))
                out = outside_box(r2)
            segsid.append(i)
            rsegs.append([r1, r2])
        
        segsid = np.array(segsid).astype(int)
        nsegs = segsid.shape[0]
        rsegs = np.array(rsegs).reshape(-1,3)
        b = b[segsid]
        p = p[segsid]
        for k, v in segprops.items():
            segprops[k] = v[segsid]
    else:
        nsegs = segsnid.shape[0]
        rsegs = np.hstack((r1, r2)).reshape(-1,3)
    
    f = open(vtkfile, 'w')
    f.write("# vtk DataFile Version 3.0\n")
    f.write("Configuration exported from OpenDiS\n")
    f.write("ASCII\n")
    f.write("DATASET UNSTRUCTURED_GRID\n")
    
    f.write("POINTS %d FLOAT\n" % (c.shape[0]+2*nsegs))
    np.savetxt(f, c, fmt='%f')
    np.savetxt(f, rsegs, fmt='%f')
    
    f.write("CELLS %d %d\n" % (1+nsegs, 9+3*nsegs))
    f.write("8 0 1 4 2 3 5 7 6\n")
    nid = np.hstack((2*np.ones((nsegs,1)), np.arange(2*nsegs).reshape(-1,2)+8))
    np.savetxt(f, nid, fmt='%d')
    
    f.write("CELL_TYPES %d\n" % (1+nsegs))
    f.write("12\n")
    np.savetxt(f, 4*np.ones(nsegs), fmt='%d')
    
    f.write("CELL_DATA %d\n" % (1+nsegs))
    
    f.write("VECTORS Burgers FLOAT\n")
    f.write("%f %f %f\n" % tuple(np.zeros(3)))
    np.savetxt(f, b, fmt='%f')
    
    f.write("VECTORS Planes FLOAT\n")
    f.write("%f %f %f\n" % tuple(np.zeros(3)))
    np.savetxt(f, p, fmt='%f')
    
    for k, v in segprops.items():
        vals = np.atleast_2d(v.T).T
        if vals.shape[0] != nsegs:
            raise ValueError('segprop value must the same size as the number of segments')
        f.write("SCALARS %s FLOAT %d\n" % (str(k), vals.shape[1]))
        f.write("LOOKUP_TABLE default\n")
        np.savetxt(f, np.vstack((np.zeros(vals.shape[1]), vals)), fmt='%f')
    
    f.close()
