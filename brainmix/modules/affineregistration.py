'''
Affine image registration.

This module implements the algorithm by Simon Baker and Iain Matthews (2004)
"Lucas-Kanade 20 Years On: A Unifying Framework"
http://www.ri.cmu.edu/pub_files/pub3/baker_simon_2004_1/baker_simon_2004_1.pdf

with improved convergence by Noppadol Chumchob and Ke Chen (2009)
"A Robust Affine Registration Method"
http://www.math.ualberta.ca/ijnam/Volume-6-2009/No-2-09/2009-02-09.pdf


Written by Anna Lakunina and Santiago Jaramillo.
See AUTHORS file for credits.

TO DO:
- does Hessian computation need to be inside loop when we've taken out the mask?
'''


import numpy as np
from numpy import math
from brainmix.modules import imregistration as imreg
import skimage.transform
import scipy.signal


def affine_transform(image, tfrm):
    '''
    Apply an affine transformation to an image (grayscale).

    Args: 
        image (np.ndarray): original image
        tfrm (np.ndarray): (3,3) homogeneous affine transformation matrix.

    Returns:
        outimg (np.ndarray): A transformed image.
    '''
    matrix = np.append(tfrm, [[0,0,1]],0)
    skTransform = skimage.transform.AffineTransform(matrix=matrix)
    outimg = skimage.transform.warp(image, skTransform, mode='nearest')
    return outimg


def affine_least_squares(source, target, tfrm, maxIterations):
    '''
    Apply modified Levenberg-Marquardt algorithm to minimize the difference in pixel
    intensities between the source and target images.

    Args:
        source (np.ndarray): source image, the one that will be transformed.
        target (np.ndarray): target image, the one that will not move.
        tfrm (np.ndarray): (3,2) initial transformation [homogeneous affine transformation matrix].
        maxIterations (int): maximum number of iterations performed by algorithm before returning a transformation

    Returns:
        tfrm (np.ndarray): (3,2) best transformation.
    '''
    identity = np.eye(2,3)
    imshape = source.shape
    (height, width) = imshape
    newtfrm = tfrm - identity
    lambdavar = 0.001
    # -- Use Scharr operator to calculate image gradient in horizontal and vertical directions --
    scharr = np.array([[-3-3j, 0-10j, +3-3j], [-10+0j, 0+0j, +10+0j], [-3+3j, 0+10j, +3+3j]])
    tgrad = scipy.signal.convolve2d(target, scharr, boundary='symm', mode='same')
    # -- Calculate current error --
    err = target - affine_transform(source, tfrm)
    bestMeanSquares = np.mean(err**2)
    # -- Pre-calculate items for the Hessian (for efficiency) --
    xdx = tgrad.real*np.arange(width)
    ydx = tgrad.real*np.arange(height)[:,np.newaxis]
    xdy = tgrad.imag*np.arange(width)
    ydy = tgrad.imag*np.arange(height)[:,np.newaxis]
    plt.clf()
    '''plt.subplot(2,2,1)
    plt.imshow(xdx, cmap='gray', interpolation='none', vmin=-5000, vmax=5000)
    plt.colorbar()
    plt.subplot(2,2,2)
    plt.imshow(ydx, cmap='gray', interpolation='none', vmin=-5000, vmax=5000)
    plt.colorbar()
    plt.subplot(2,2,3)
    plt.imshow(xdy, cmap='gray', interpolation='none', vmin=-5000, vmax=5000)
    plt.colorbar()
    plt.subplot(2,2,4)
    plt.imshow(ydy, cmap='gray', interpolation='none', vmin=-5000, vmax=5000)
    plt.colorbar()
    plt.waitforbuttonpress()'''
    (heightSq,widthSq) = np.array(imshape)**2
    displacement = 1.0
    '''Jacobian = np.array([np.sum(xdx), 
                             np.sum(ydx), 
                             np.sum(tgrad.real),
                             np.sum(xdy), 
                             np.sum(ydy), 
                             np.sum(tgrad.imag)])[np.newaxis]'''
    tHessian = np.array([[np.sum(xdx**2), np.sum(xdx*ydx), np.sum(xdx*tgrad.real), np.sum(xdx*xdy), np.sum(xdx*ydy), np.sum(xdx*tgrad.imag)],
                         [0, np.sum(ydx**2), np.sum(ydx*tgrad.real), np.sum(ydx*xdy), np.sum(ydx*ydy), np.sum(ydx*tgrad.imag)],
                         [0, 0, np.sum(tgrad.real**2), np.sum(tgrad.real*xdy), np.sum(tgrad.real*ydy), np.sum(tgrad.real*tgrad.imag)],
                         [0, 0, 0, np.sum(xdy**2), np.sum(xdy*ydy), np.sum(xdy*tgrad.imag)],
                         [0, 0, 0, 0, np.sum(ydy**2), np.sum(ydy*tgrad.imag)],
                         [0, 0, 0, 0, 0, np.sum(tgrad.imag**2)]])
    tHessian += np.triu(tHessian,1).T
    #print tHessian
    '''plt.imshow(tHessian, cmap='gray', interpolation='none')
    plt.colorbar()
    plt.waitforbuttonpress()'''
    # NOTE: using range() for compatibility with Python3
    for iteration in range(maxIterations):
        #print lambdavar
        gradient = np.array([np.sum(err*xdx),
                             np.sum(err*ydx),
                             np.sum(err*tgrad.real),
                             np.sum(err*xdy),
                             np.sum(err*ydy), 
                             np.sum(err*tgrad.imag)])
        #print gradient
        tHessianDiag = np.diag(lambdavar*np.diag(tHessian))
        updateinv = np.dot(np.linalg.inv(tHessian+tHessianDiag),gradient).reshape(2,3)
        updateinv = np.vstack((updateinv+identity, np.array([0,0,1])))
        update = np.linalg.inv(updateinv)
        #print update
        newtfrmfull = np.vstack((newtfrm+identity, np.array([0,0,1])))
        attempt = np.dot(newtfrmfull,update)
        attempt = attempt[:2,:]
        #print attempt
        displacement = np.sqrt(update[0,2]*update[0,2] + update[1,2]*update[1,2]) + \
                       0.25 * np.sqrt(widthSq + heightSq) * np.sum(np.absolute(update[:,:2]))
        err = target - affine_transform(source, attempt)
        if np.mean(err**2)<bestMeanSquares:
            bestMeanSquares = np.mean(err**2)
            print bestMeanSquares
            # NOTE: Numpy 1.7 or newer has np.copyto() which should be faster than copy()
            newtfrm = attempt-identity # We need to copy values, tfrm=attempt would just make a reference to 'attempt'
            lambdavar /= 10.0 # FIXME: we may need to prevent lambda from becoming 0
        else:
            lambdavar *= 10.0
        if displacement < 0.001:
            break
    print newtfrm+identity
    return newtfrm+identity
            

def affine_registration(source, target, pyramidDepth, minLevel=0, downscale=2, debug=False):
    '''
    Find affine transformation that registers source image to the target image.

    This function computes the image pyramid for source and target and calculates the transformation
    that minimizes the least-square error between images (starting at the lowest resolution).

    Args:
        source (np.ndarray): source image, the one that will be transformed.
        target (np.ndarray): target image, the one that will not move.
        pyramidDepth (int): number of pyramid levels, in addition to the original.
        minLevel (int): 0 for original level, >0 for coarser resolution.
    
    Return:
        tfrm (np.ndarray):
    '''
    sourcePyramid = tuple(skimage.transform.pyramid_gaussian(source, max_layer=pyramidDepth, downscale=downscale))
    targetPyramid = tuple(skimage.transform.pyramid_gaussian(target, max_layer=pyramidDepth, downscale=downscale))
    # -- compute small scale rigid body transformation to provide the initial guess for the affine transformation --
    '''rtfrm = imreg.rigid_body_registration(sourcePyramid[minLevel], targetPyramid[minLevel], pyramidDepth-minLevel)
    rotmatrix = np.array([[math.cos(rtfrm[0]), -math.sin(rtfrm[0])], [math.sin(rtfrm[0]), math.cos(rtfrm[0])]])
    tfrm = np.append(rotmatrix, [[rtfrm[1]], [rtfrm[2]]], 1)
    tfrm[:,-1] /= pow(downscale,pyramidDepth-minLevel)'''
    tfrm = np.array([[1,0,0],[0,1,0]])
    for layer in range(pyramidDepth, minLevel-1, -1):
        tfrm[:,-1] *= downscale  # Scale translation for next level in pyramid
        tfrm = affine_least_squares(sourcePyramid[layer],targetPyramid[layer], tfrm, 10*2**(layer-1))
        toptfrm = np.concatenate((tfrm[:,0:2],tfrm[:,-1:]*pow(downscale,layer)), axis=1);
        if debug:
            pass
            #print 'Layer {0}: {1}x{2}'.format(layer, *targetPyramid[layer].shape)
            #print 'th={0:0.4}, x={1:0.1f} , y={2:0.1f}'.format(*toptfrm) ### DEBUG
    return toptfrm



if __name__=='__main__':

    import skimage.io
    import matplotlib.pyplot as plt
    
    #sourceimg = skimage.io.imread('/data/brainmix_data/test043_TL/p1-D4-01b.jpg',as_grey=True)
    #tfrm = np.array([[1,0.2,40],[0.3,0.9,50]])
    #targetimg = affine_transform(sourceimg, tfrm)
    #targetimg = skimage.io.imread('/data/brainmix_data/test043_TL/p1-D3-01b.jpg',as_grey=True) 
    
    sourceimg = skimage.io.imread('/data/brainmix_data/test043_TL/p1-F1-01b.jpg',as_grey=True)
    targetimg = skimage.io.imread('/data/brainmix_data/test043_TL/p1-E6-01b.jpg',as_grey=True)
    
    CASE = 1
    
    if CASE==0:
        tfrm = affine_least_squares(sourceimg, targetimg, np.eye(2,3), 10)
        outimg = affine_transform(sourceimg, tfrm)
        plt.imshow(outimg)
    
    if CASE == 1:
        tfrm = affine_registration(sourceimg, targetimg, 7, 3, debug=True)
        print tfrm
        outimg = affine_transform(sourceimg, tfrm)
        plt.subplot(1,4,1)
        plt.imshow(sourceimg, cmap='PiYG')
        plt.title('source')
        plt.subplot(1,4,2)
        plt.imshow(targetimg, cmap='PiYG')
        plt.title('target')
        plt.subplot(1,4,3)
        plt.imshow(outimg, cmap='PiYG')
        plt.title('transformed source')
        plt.subplot(1,4,4)
        plt.imshow(targetimg-outimg, cmap='PiYG')
        plt.title('difference')

    
