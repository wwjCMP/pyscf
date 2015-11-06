import numpy as np
from pyscf import dft
from pyscf.lib import logger
from pyscf.lib.numpy_helper import cartesian_prod
import pyscf.dft
from pyscf.pbc import tools

def gen_uniform_grids(cell):
    '''Generate a uniform real-space grid consistent w/ samp thm; see MH (3.19).

    Args:
        cell : instance of :class:`Cell`

    Returns:
        coords : (ngx*ngy*ngz, 3) ndarray
            The real-space grid point coordinates.

    '''
    ngs = 2*np.asarray(cell.gs)+1
    qv = cartesian_prod([np.arange(x) for x in ngs])
    invN = np.diag(1./ngs)
    coords = np.dot(qv, np.dot(cell._h, invN).T)
    return coords

class UniformGrids(object):
    '''Uniform Grid class.'''

    def __init__(self, cell):
        self.cell = cell
        self.coords = None
        self.weights = None
        self.stdout = cell.stdout
        self.verbose = cell.verbose

    def setup_grids_(self, cell=None):
        if cell == None: cell = self.cell

        self.coords = gen_uniform_grids(self.cell)
        self.weights = np.ones(self.coords.shape[0])
        self.weights *= cell.vol/self.weights.shape[0]

        return self.coords, self.weights

    def dump_flags(self):
        logger.info(self, 'Uniform grid')

    def kernel(self, cell=None):
        self.dump_flags()
        return self.setup_grids()


def gen_becke_grids(cell, atom_grid={}, radi_method=dft.radi.gauss_chebyshev,
                    level=3, prune_scheme=dft.gen_grid.treutler_prune):
    '''real-space grids using Becke scheme

    Args:
        cell : instance of :class:`Cell`

    Returns:
        coords : (ngx*ngy*ngz, 3) ndarray
            The real-space grid point coordinates.
        weights : (ngx*ngy*ngz) ndarray
    '''
    scell = tools.super_cell(cell, cell.nimgs)
    atom_grids_tab = dft.gen_grid.gen_atomic_grids(scell, atom_grid, radi_method,
                                                   level, prune_scheme)
    coords, weights = dft.gen_grid.gen_partition(scell, atom_grids_tab)

    # search for grids in unit cell
    #b1,b2,b3 = np.linalg.inv(h).T  # reciprocal lattice
    #np.einsum('kj,ij->ki', coords, (b1,b2,b3))
    c111 = cell._h[:,0] + cell._h[:,1] + cell._h[:,2]
    d1 = np.dot(coords, np.linalg.inv(cell._h))
    d2 = np.dot(coords-c111, np.linalg.inv(cell._h))
    # d1[:,0]>0 and d1[:,1] > 0 and d1[:,2] > 0 and
    # d2[:,0]<0 and d2[:,1] < 0 and d2[:,2] < 0
    mask = np.logical_and(reduce(np.logical_and, (d1>=0).T),
                          reduce(np.logical_and, (d2< 0).T))
    return coords[mask], weights[mask]


class BeckeGrids(pyscf.dft.gen_grid.Grids):
    '''Becke, JCP, 88, 2547 (1988)'''
    def __init__(self, cell):
        self.cell = cell
        pyscf.dft.gen_grid.Grids.__init__(self, cell)

    def setup_grids_(self, cell=None):
        if cell is None: cell = self.cell
        self.coords, self.weights = gen_becke_grids(self.cell, self.atom_grid)
        return self.coords, self.weights

if __name__ == '__main__':
    import pyscf.pbc.gto as pgto

    L = 4.
    n = 30
    cell = pgto.Cell()
    cell.h = np.diag([L,L,L])
    cell.gs = np.array([n,n,n])

    cell.atom = '''He     0.    0.       1.
                   He     1.    0.       1.'''
    cell.basis = {'He': [[0, (1.0, 1.0)]]}
    cell.build()
    g = BeckeGrids(cell)
    g.build_()
