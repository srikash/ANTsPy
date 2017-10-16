"""
Create a static 2D image of a 2D ANTsImage
or a tile of slices from a 3D ANTsImage
"""


__all__ = ['plot',
           'plot_directory']

import fnmatch
import math
import os
import warnings

from   matplotlib import gridspec
import matplotlib.pyplot as plt
import numpy as np

from ..core import ants_image_io as iio2


def plot(image, overlay=None, cmap='Greys_r', overlay_cmap='jet', overlay_alpha=0.9,
         axis=0, nslices=12, slices=None, ncol=4, slice_buffer=0, white_bg=False,
         filename=None):
    """
    Plot an ANTsImage
    
    ANTsR function: `plot`

    Arguments
    ---------
    image : ANTsImage
        image to plot

    overlay : ANTsImage (optional)
        image to overlay on base image

    cmap : string
        colormap to use for base image. See matplotlib.

    overlay_cmap : string
        colormap to use for overlay images, if applicable. See matplotlib.

    overlay_alpha : float
        level of transparency for any overlays. Smaller value means 
        the overlay is more transparent. See matplotlib.

    axis : integer
        which axis to plot along if image is 3D

    nslices : integer
        number of slices to plot if image is 3D

    slices : list or tuple of integers
        specific slice indices to plot if image is 3D. 
        If given, this will override `nslices`.
        This can be absolute array indices (e.g. (80,100,120)), or
        this can be relative array indices (e.g. (0.4,0.5,0.6))

    ncol : integer (default is 4)
        Number of columns to have on the plot if image is 3D.

    slice_buffer : integer (default is 0)
        how many slices to buffer when finding the non-zero slices of
        a 3D images. So, if slice_buffer = 10, then the first slice
        in a 3D image will be the first non-zero slice index plus 10 more
        slices.

    white_bg : boolean (default is False)
        if True, the background of the image(s) will be white.
        if False, the background of the image(s) will be black

    filename : string (optional)
        if given, the resulting image will be saved to this file

    Example
    -------
    >>> ## 2D images ##
    >>> import ants
    >>> img = ants.image_read(ants.get_data('r16'))
    >>> ants.plot(img)
    >>> overlay = (img.kmeans_segmentation(k=3)['segmentation']==3)*(img.clone())
    >>> ants.plot(img, overlay)
    >>> ## 3D images ##
    >>> import ants
    >>> img3d = ants.image_read(ants.get_data('ch2'))
    >>> ants.plot(img3d)
    >>> ants.plot(img3d, axis=0, nslices=5) # slice numbers
    >>> ants.plot(img3d, axis=1, nslices=5) # different axis
    >>> ants.plot(img3d, axis=2, nslices=5) # different slices
    >>> ants.plot(img3d, nslices=1) # one slice
    >>> ants.plot(img3d, slices=(50,70,90)) # absolute slices
    >>> ants.plot(img3d, slices=(0.4,0.6,0.8)) # relative slices
    >>> ants.plot(img3d, slices=50) # one absolute slice
    >>> ants.plot(img3d, slices=0.6) # one relative slice
    >>> ## Overlay Example ##
    >>> import ants
    >>> img = ants.image_read(ants.get_data('ch2'))
    >>> overlay = img.clone()
    >>> overlay = overlay*(overlay>105.)
    >>> ants.plot(img, overlay)
    """
    # need this hack because of a weird NaN warning (not an exception) from
    # matplotlib with overlays
    warnings.simplefilter('ignore')

    # Plot 2D image
    if image.dimension == 2:
        img_arr = image.numpy()

        if overlay is not None:
            ov_arr = overlay.numpy()
            ov_arr[np.abs(ov_arr) == 0] = np.nan

        fig, ax = plt.subplots()

        ax.imshow(img_arr, cmap=cmap)

        if overlay is not None:
            ax.imshow(ov_arr, alpha=overlay_alpha, cmap=overlay_cmap)

        plt.axis('off')
        if filename is not None:
            plt.savefig(filename)
            plt.close(fig)
        else:
            plt.show()

    # Plot 3D image
    elif image.dimension == 3:
        img_arr = image.numpy()
        # reorder dims so that chosen axis is first
        img_arr = np.rollaxis(img_arr, axis)

        if overlay is not None:
            ov_arr = overlay.numpy()
            ov_arr[np.abs(ov_arr) == 0] = np.nan
            ov_arr = np.rollaxis(ov_arr, axis)

        if slices is None:
            if not isinstance(slice_buffer, (list, tuple)):
                slice_buffer = (slice_buffer, slice_buffer)
            nonzero = np.where(np.abs(img_arr)>0)[0]
            min_idx = nonzero[0] + slice_buffer[0]
            max_idx = nonzero[-1] - slice_buffer[1]
            slice_idxs = np.linspace(min_idx, max_idx, nslices).astype('int')
        else:
            if isinstance(slices, (int,float)):
                slices = [slices]
            if slices[0] < 1:
                slices = [int(s*img_arr.shape[0]) for s in slices]
            slice_idxs = slices
            nslices = len(slices)

        # only have one row if nslices <= 6 and user didnt specify ncol
        if (nslices <= 6) and (ncol==4):
            ncol = nslices

        # calculate grid size
        nrow = math.ceil(nslices / ncol)

        xdim = img_arr.shape[1]
        ydim = img_arr.shape[2]

        fig = plt.figure(figsize=((ncol+1)*1.5*(ydim/xdim), (nrow+1)*1.5)) 

        gs = gridspec.GridSpec(nrow, ncol,
                 wspace=0.0, hspace=0.0, 
                 top=1.-0.5/(nrow+1), bottom=0.5/(nrow+1), 
                 left=0.5/(ncol+1), right=1-0.5/(ncol+1)) 

        slice_idx_idx = 0
        for i in range(nrow):
            for j in range(ncol):
                if slice_idx_idx < len(slice_idxs):
                    im = img_arr[slice_idxs[slice_idx_idx]]
                    if white_bg:
                        im[im<(im.min()+1e-5)] = None
                    ax = plt.subplot(gs[i,j])
                    ax.imshow(im, cmap=cmap)
                    if overlay is not None:
                        ov = ov_arr[slice_idxs[slice_idx_idx]]
                        ax.imshow(ov, alpha=overlay_alpha, cmap=overlay_cmap)
                    ax.axis('off')
                    slice_idx_idx += 1

        if filename is not None:
            plt.savefig(filename)
            plt.close(fig)
        else:
            plt.show()

        # turn warnings back to default
        warnings.simplefilter('default')


def plot_directory(directory, recursive=False, regex='*', 
                   save_prefix='', save_suffix='', **kwargs):
    """
    Create and save an ANTsPy plot for every image matching a given regular
    expression in a directory, optionally recursively. This is a good function
    for quick visualize exploration of all of images in a directory 
    
    ANTsR function: N/A

    Arguments
    ---------
    directory : string
        directory in which to search for images and plot them

    recursive : boolean
        If true, this function will search through all directories under 
        the given directory recursively to make plots.
        If false, this function will only create plots for images in the
        given directory

    regex : string
        regular expression used to filter out certain filenames or suffixes

    save_prefix : string
        sub-string that will be appended to the beginning of all saved plot filenames. 
        Default is to add nothing.

    save_suffix : string
        sub-string that will be appended to the end of all saved plot filenames. 
        Default is add nothing.

    kwargs : keyword arguments
        any additional arguments to pass onto the `ants.plot` function.
        e.g. overlay, alpha, cmap, etc. See `ants.plot` for more options.

    Example
    -------
    >>> import ants
    >>> ants.plot_directory(directory='~/desktop/testdir',
                            recursive=False, regex='*')
    """
    def has_acceptable_suffix(fname):
        suffixes = {'.nii.gz'}
        return sum([fname.endswith(sx) for sx in suffixes]) > 0

    if directory.startswith('~'):
        directory = os.path.expanduser(directory)

    if not os.path.isdir(directory):
        raise ValueError('directory %s does not exist!' % directory)

    for root, dirnames, fnames in os.walk(directory):
        for fname in fnames:
            if fnmatch.fnmatch(fname, regex) and has_acceptable_suffix(fname):
                load_fname = os.path.join(root, fname)
                fname = fname.replace('.'.join(fname.split('.')[1:]), 'png')
                fname = fname.replace('.png', '%s.png' % save_suffix)
                fname = '%s%s' % (save_prefix, fname)
                save_fname = os.path.join(root, fname)
                img = iio2.image_read(load_fname)
                if img.dimension > 2:
                    for axis_idx in range(img.dimension):
                        filename = save_fname.replace('.png', '_axis%i.png' % axis_idx)
                        ncol = int(math.sqrt(img.shape[axis_idx]))
                        plot(img, axis=axis_idx, nslices=img.shape[axis_idx], ncol=ncol,
                             filename=filename, **kwargs)
                else:
                    filename = save_fname
                    plot(img, filename=filename, **kwargs)                    







