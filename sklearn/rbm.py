""" Restricted Boltzmann Machine
"""

# Author: Yann N. Dauphin <dauphiya@iro.umontreal.ca>
# License: BSD Style.

import numpy as np

from .base import BaseEstimator, TransformerMixin
from .utils import array2d, check_random_state


class RBM(BaseEstimator, TransformerMixin):
    """
    Restricted Boltzmann Machine (RBM)
    
    A Restricted Boltzmann Machine with binary visible units and
    binary hiddens. Parameters are estimated using Stochastic Maximum
    Likelihood (SML).
    
    The time complexity of this implementation is ``O(n ** 2)`` assuming
    n ~ n_samples ~ n_features.
    
    Parameters
    ----------
    n_components : int, optional
        Number of binary hidden units
    epsilon : float, optional
        Learning rate to use during learning. It is *highly* recommended
        to tune this hyper-parameter. Possible values are 10**[0., -3.].
    n_samples : int, optional
        Number of fantasy particles to use during learning
    epochs : int, optional
        Number of epochs to perform during learning
    verbose: bool, optional
        When True (False by default) the method outputs the progress
        of learning after each epoch.
    random_state : RandomState or an int seed (0 by default)
        A random number generator instance to define the state of the
        random permutations generator.
    
    Attributes
    ----------
    W : array-like, shape (n_visibles, n_components), optional
        Weight matrix, where n_visibles in the number of visible
        units and n_components is the number of hidden units.
    b : array-like, shape (n_components,), optional
        Biases of the hidden units
    c : array-like, shape (n_visibles,), optional
        Biases of the visible units
    
    Examples
    --------
    
    >>> import numpy as np
    >>> from sklearn.rbm import RBM
    >>> X = np.array([[0, 0, 0], [0, 1, 1], [1, 0, 1], [1, 1, 1]])
    >>> model = RBM(n_components=2)
    >>> model.fit(X)
    
    References
    ----------
    
    [1] Hinton, G. E., Osindero, S. and Teh, Y. A fast learning algorithm for
        deep belief nets. Neural Computation 18, pp 1527-1554.
    """
    def __init__(self, n_components=1024,
                       epsilon=0.1,
                       n_samples=10,
                       epochs=10,
                       verbose=False,
                       random_state=0):
        self.n_components = n_components
        self.epsilon = epsilon
        self.n_samples = n_samples
        self.epochs = epochs
        self.verbose = verbose
        self.random_state = check_random_state(random_state)
    
    def _sigmoid(self, x):
        """
        Implements the logistic function.
        
        Parameters
        ----------
        x: array-like, shape (M, N)

        Returns
        -------
        x_new: array-like, shape (M, N)
        """
        return 1. / (1. + np.exp(-np.maximum(np.minimum(x, 30), -30)))
    
    def transform(self, v):
        """
        Computes the probabilities P({\bf h}_j=1|{\bf v}).
        
        Parameters
        ----------
        v: array-like, shape (n_samples, n_visibles)

        Returns
        -------
        h: array-like, shape (n_samples, n_components)
        """
        return self.mean_h(v)
    
    def mean_h(self, v):
        """
        Computes the probabilities P({\bf h}_j=1|{\bf v}).
        
        Parameters
        ----------
        v: array-like, shape (n_samples, n_visibles)

        Returns
        -------
        h: array-like, shape (n_samples, n_components)
        """
        return self._sigmoid(np.dot(v, self.W) + self.b)
    
    def sample_h(self, v):
        """
        Sample from the distribution P({\bf h}|{\bf v}).
        
        Parameters
        ----------
        v: array-like, shape (n_samples, n_visibles)
        
        Returns
        -------
        h: array-like, shape (n_samples, n_components)
        """
        return self.random_state.binomial(1, self.mean_h(v))
    
    def mean_v(self, h):
        """
        Computes the probabilities P({\bf v}_i=1|{\bf h}).
        
        Parameters
        ----------
        h: array-like, shape (n_samples, n_components)
        
        Returns
        -------
        v: array-like, shape (n_samples, n_visibles)
        """
        return self._sigmoid(np.dot(h, self.W.T) + self.c)
    
    def sample_v(self, h):
        """
        Sample from the distribution P({\bf v}|{\bf h}).
        
        Parameters
        ----------
        h: array-like, shape (n_samples, n_components)
        
        Returns
        -------
        v: array-like, shape (n_samples, n_visibles)
        """
        return self.random_state.binomial(1, self.mean_v(h))
    
    def free_energy(self, v):
        """
        Computes the free energy
        \mathcal{F}({\bf v}) = - \log \sum_{\bf h} e^{-E({\bf v},{\bf h})}.
        
        Parameters
        ----------
        v: array-like, shape (n_samples, n_visibles)
        
        Returns
        -------
        free_energy: array-like, shape (n_samples,)
        """
        return - np.dot(v, self.c) \
            - np.log(1. + np.exp(np.dot(v, self.W) + self.b)).sum(1)
    
    def gibbs(self, v):
        """
        Perform one Gibbs sampling step.
        
        Parameters
        ----------
        v: array-like, shape (n_samples, n_visibles)
        
        Returns
        -------
        v_new: array-like, shape (n_samples, n_visibles)
        """
        h_ = self.sample_h(v)
        v_ = self.sample_v(h_)
        
        return v_
    
    def _fit(self, v_pos):
        """
        Adjust the parameters to maximize the likelihood of {\bf v}
        using Stochastic Maximum Likelihood (SML) [1].
        
        Parameters
        ----------
        v_pos: array-like, shape (n_samples, n_visibles)
        
        Returns
        -------
        pseudo_likelihood: array-like, shape (n_samples,), optional
            Pseudo Likelihood estimate for this batch.
        
        References
        ----------
        [1] Tieleman, T. Training Restricted Boltzmann Machines using
            Approximations to the Likelihood Gradient. International Conference
            on Machine Learning (ICML) 2008
        """
        h_pos = self.mean_h(v_pos)
        v_neg = self.sample_v(self.h_samples)
        h_neg = self.mean_h(v_neg)
        
        self.W += self.epsilon * (np.dot(v_pos.T, h_pos)
            - np.dot(v_neg.T, h_neg)) / self.n_samples
        self.b += self.epsilon * (h_pos.mean(0) - h_neg.mean(0))
        self.c += self.epsilon * (v_pos.mean(0) - v_neg.mean(0))
        
        self.h_samples = self.random_state.binomial(1, h_neg)
        
        return self.pseudo_likelihood(v_pos)
    
    def pseudo_likelihood(self, v):
        """
        Compute the pseudo-likelihood of {\bf v}.
        
        Parameters
        ----------
        v: array-like, shape (n_samples, n_visibles)
        
        Returns
        -------
        pseudo_likelihood: array-like, shape (n_samples,)
        """
        fe = self.free_energy(v)
        
        v_ = v.copy()
        i_ = self.random_state.randint(0, v.shape[1], v.shape[0])
        v_[range(v.shape[0]), i_] = v_[range(v.shape[0]), i_] == 0
        fe_ = self.free_energy(v_)
        
        return v.shape[1] * np.log(self._sigmoid(fe_ - fe))
    
    def fit(self, X, y=None):
        """
        Fit the model to the data X.
        
        Parameters
        ----------
        X: array-like, shape (n_samples, n_features)
            Training data, where n_samples in the number of samples
            and n_features is the number of features.
        """
        X = array2d(X)
        
        self.W = np.asarray(self.random_state.normal(0, 0.01,
            (X.shape[1], self.n_components)), dtype=X.dtype)
        self.b = np.zeros(self.n_components, dtype=X.dtype)
        self.c = np.zeros(X.shape[1], dtype=X.dtype)
        self.h_samples = np.zeros((self.n_samples, self.n_components),
            dtype=X.dtype)
        
        inds = range(X.shape[0])
        
        np.random.shuffle(inds)
        
        n_batches = int(np.ceil(len(inds) / float(self.n_samples)))
        
        for epoch in range(self.epochs):
            pl = 0.
            for minibatch in range(n_batches):
                pl += self._fit(X[inds[minibatch::n_batches]]).sum()
            pl /= X.shape[0]
            
            if self.verbose:
                print "Epoch %d, Pseudo-Likelihood = %.2f" % (epoch, pl)
    
    def fit_transform(self, X, y=None, verbose=False):
        """
        Fit the model to the data X and transform it.
        
        Parameters
        ----------
        X: array-like, shape (n_samples, n_features)
            Training data, where n_samples in the number of samples
            and n_features is the number of features.
        """
        self.fit(X, y)
        
        return self.transform(X)


def main():
    pass


if __name__ == '__main__':
    main()

