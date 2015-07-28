#!/usr/bin/env python
"""This module contains functions necessary to produce statistical results of the fisher formalism from a given galaxy"""

#import defaults

import functions as fns

import math

import numpy as np

from copy import deepcopy

import galfun


#steps defined here because it is where its relevant (derivatives).
class steps: 
    """Define the steps for derivatives of each individual parameter."""
    def __init__(self, params):
        self.dict = dict()
        self.dict['flux'] = params['flux'] * .01
        self.dict['hlr'] = params['hlr'] *.01
        self.dict['e1'] = .01
        self.dict['e2'] = .01
        self.dict['x0'] = .01
        self.dict['y0'] = .01
        #steps['q'] = orig_params['q']*.01
        #steps['beta'] = orig_params['beta']*.01


def partialDifferentiate(func, param, step, **kwargs):
    """Partially derive f with respect to a parameter with a certain step.
    We are assuming that the function has a certain structure, namely, one of its arguments is a dictionary of 
    variables that can be changed and other (**kwargs) arguments are requisites or extra variables
    the function needs to be evaluated. This is because we are assuming we can add step to params[parameter]."""

    def Dfunc(params):
        """Evaluate the partial derivative at params."""
        params_up = deepcopy(params) #avoids altering params later.
        params_up[param] += step #increment the value of the parameter by step. 

        params_down = deepcopy(params)
        params_down[param] -= step 

        return (func(params_up, **kwargs) - func(params_down, **kwargs)) / (2 * steps[param] )
    return Dfunc

def secondPartialDifferentiate(func, param1, param2, step1, step2,**kwargs): 
    Df = partialDifferentiate(func, param1, step1 **kwargs)
    return partialDifferentiate(Df, param2, step2)

def chi2(params, gal_image, sigma_n, **kwargs): 
    """Returns chi2 given the modified parameters and the original galaxy, assume sigma_n is the same for all pixels -- OWN"""
    return ((((gal_image - galfun.drawGalaxies(params, **kwargs)).array/ (sigma_n)))**2).sum()

class fisher_analysis:
    """Given a galaxy image and the appropiate parameters that describe it, will produce a fisher objec that contains the analysis of it using the fisher formalism"""

    def __init__(self, galaxies, sigma_n): 

        self.galaxies = galaxies
        self.steps = steps(self.params).dict
        self.sigma_n = float(sigma_n) 
        self.param_names = galaxies.model_params
        self.num_params = len(self.param_names)

        self.derivatives_images = self.derivativesImages()
        self.fisher_matrix_images = self.fisherMatrixImages()
        self.fisher_matrix = self.fisherMatrix()
        self.fisher_matrix_chi2 = self.fisherMatrixChi2()
        self.covariance_matrix = self.covarianceMatrix()
        self.correlation_matrix = self.correlationMatrix()
        self.second_derivatives_images = self.secondDerivativesImages()
        self.bias_matrix_images = self.biasMatrixImages()
        self.bias_matrix = self.biasMatrix()
        self.bias_images = self.biasImages()
        self.biases = self.biases()      

    def derivativesImages(self):
        #create a dictionary with the derivatives of the model with respect to each parameter.
        return {self.param_names[i]:fns.partialDifferentiate(func = fns.drawGalaxies, parameter = self.param_names[i], step = self.step[self.param_names[i]])(self.params) for i in range(self.num_params)}

    def fisherMatrixImages(self):
        FisherM_images = {}
        for i in range(self.num_params): 
            for j in range(self.num_params): 
                FisherM_images[self.param_names[i],self.param_names[j]] = (self.derivatives_images[self.param_names[i]] * self.derivatives_images[self.param_names[j]]) /(self.sigma_n**2)
        return FisherM_images

    def fisherMatrix(self):
        FisherM = {}
        for i in range(self.num_params): 
            for j in range(self.num_params): 
                FisherM[self.param_names[i],self.param_names[j]] = self.fisher_matrix_images[self.param_names[i],self.param_names[j]].sum() #sum over all pixels. 
        return FisherM

    def fisherMatrixChi2(self):
        FisherM_chi2 = {}
        for i in range(self.num_params): 
            for j in range(self.num_params): 
                FisherM_chi2[self.param_names[i],self.param_names[j]] = .5 * fns.secondPartialDifferentiate(chi2, self.param_names[i], self.param_names[j], self.steps[self.param_names[i]], self.steps[self.param_names[j]], sigma_n = self.sigma_n, gal_image = self.galaxies.image)(self.params)

        return FisherM_chi2

    def covarianceMatrix(self):
        #Covariance matrix is inverse of Fisher Matrix:
        CovM = {}
        FisherM_array = np.array([[self.fisher_matrix[self.param_names[i],self.param_names[j]] for i in range(self.num_params)] for j in range(self.num_params)])#convert to numpy array because it can be useful.
        CovM_array = np.linalg.inv(FisherM_array) #need to be an array to inverse.

        for i in range(self.num_params):
            for j in range(self.num_params):
                CovM[self.param_names[i],self.param_names[j]] = CovM_array[i][j]

        return CovM
    
    def correlationMatrix(self):
        correlation_matrix = {}
        for i in range(self.num_params):
            for j in range(self.num_params):
                correlation_matrix[self.param_names[i],self.param_names[j]] = self.covariance_matrix[self.param_names[i],self.param_names[j]] / math.sqrt(self.covariance_matrix[self.param_names[i],self.param_names[i]] * self.covariance_matrix[self.param_names[j],self.param_names[j]])

        return correlation_matrix

    def secondDerivativesImages(self):
        secondDs_gal = {}
        for i in range(self.num_params): 
            for j in range(self.num_params):
                secondDs_gal[self.param_names[i],self.param_names[j]] = secondPartialDifferentiate(galfun.drawGalaxy, self.param_names[i], self.param_names[j], self.steps[self.param_names[i]], self.steps[self.param_names[j]])(self.params)

        return secondDs_gal

    def biasMatrixImages(self):
        BiasM_images = {}
        for i in range(self.num_params): 
            for j in range(self.num_params): 
                for k in range(self.num_params): 
                    BiasM_images[self.param_names[i],self.param_names[j],self.param_names[k]] = (self.derivatives_images[self.param_names[i]] * self.second_derivatives_images[self.param_names[j],self.param_names[k]]) / (self.sigma_n**2)

        return BiasM_images

    def biasMatrix(self):
        BiasM = {}
        for i in range(self.num_params):
            for  j in range(self.num_params):
                for k in range(self.num_params):
                    BiasM[self.param_names[i],self.param_names[j],self.param_names[k]] = self.bias_matrix_images[self.param_names[i],self.param_names[j],self.param_names[k]].sum()

        return BiasM

    def biasImages(self):
        #now we want bias of each parameter per pixel, so we can see how each parameter contributes.
        bias_images = {}
        for i in range(self.num_params):
            sumation = 0 
            for j in range(self.num_params):
                for k in range(self.num_params):
                    for l in range(self.num_params):
                        sumation += self.covariance_matrix[self.param_names[i],self.param_names[j]]*self.covariance_matrix[self.param_names[k],self.param_names[l]]*self.bias_matrix_images[self.param_names[j],self.param_names[k],self.param_names[l]]
            bias_images[self.param_names[i]] = (-.5) * sumation

        return bias_images


    def biases(self):
        return {self.param_names[i]:self.bias_images[self.param_names[i]].sum() for i in range(self.num_params)}





