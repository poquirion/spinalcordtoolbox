#!/usr/bin/env python
#########################################################################################
#
#
#
# ---------------------------------------------------------------------------------------
# Copyright (c) 2014 Polytechnique Montreal <www.neuro.polymtl.ca>
# Authors: Camille Van Assel
#
#
# About the license: see the file LICENSE.TXT
#########################################################################################


import time
from msct_parser import Parser
import sys
import os
import numpy as np
import sct_utils as sct
from msct_image import Image
import random

#MAIN

def main():
    # Initialisation
    start_time_total = time.time()
    os.environ["ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS"] = "1"

    # Initialise the parser
    parser = Parser(__file__)
    parser.add_option(name="-f",
                      type_value="folder",
                      description="folder of input image and segmentation",
                      mandatory=False,
                      example="data_patients")
    parser.add_option(name="-i",
                      type_value="file",
                      description="Image source.",
                      mandatory=False,
                      example="src.nii.gz")
    parser.add_option(name="-d",
                      type_value="file",
                      description="Image destination.",
                      mandatory=False,
                      example="dest.nii.gz")
    parser.add_option(name="-iseg",
                      type_value="file",
                      description="Segmentation source.",
                      mandatory=False,
                      example="src_seg.nii.gz")
    parser.add_option(name="-dseg",
                      type_value="file",
                      description="Segmentation destination.",
                      mandatory=False,
                      example="dest_seg.nii.gz")
    parser.add_option(name="-t",
                      type_value="file",
                      description="image which will be modified",
                      mandatory=False,
                      example="im.nii.gz")
    parser.add_option(name="-tseg",
                      type_value="file",
                      description="Segmentation of the image wich will be modified.",
                      mandatory=False,
                      example="dest_seg.nii.gz")
    parser.add_option(name="-lx",
                      type_value="int",
                      description="size of the image at x",
                      mandatory=True,
                      example="50")
    parser.add_option(name="-ly",
                      type_value="int",
                      description="size of the image at y",
                      mandatory=True,
                      example="50")
    parser.add_option(name="-nb",
                      type_value="int",
                      description="number of random slice we apply the wrap on",
                      mandatory=True,
                      example="31")
    parser.add_option(name="-nw",
                      type_value="int",
                      description="number of random wrap we generate",
                      mandatory=True,
                      example='15')
    parser.add_option(name="-o",
                      type_value='str',
                      description="nameof the output folder",
                      mandatory=False)
    parser.add_option(name="-v",
                      type_value="multiple_choice",
                      description="""Verbose.""",
                      mandatory=False,
                      default_value='1',
                      example=['0', '1', '2'])
    parser.add_option(name="-cpu-nb",
                      type_value="int",
                      description="Number of CPU used for straightening. 0: no multiprocessing. If not provided, "
                                  "it uses all the available cores.",
                      mandatory=False,
                      example="8")
    parser.add_option(name="-all-slices",
                      type_value="multiple_choice",
                      description=" ",
                      mandatory=False,
                      default_value='0',
                      example=['0','1'])
    parser.add_option(name="-center-seg",
                      type_value="multiple_choice",
                      description=" ",
                      mandatory=False,
                      default_value='0',
                      example=['0', '1'])

    # get argument
    arguments = parser.parse(sys.argv[1:])
    fname_size_x = arguments['-lx']
    fname_size_y = arguments['-ly']
    nbre_slice = arguments['-nb']
    nbre_wrap = arguments['-nw']
    verbose = int(arguments['-v'])

    v = 0
    if verbose == 2:
        v = 1
    if "-cpu-nb" in arguments:
        cpu_number = int(arguments["-cpu-nb"])
    if '-f' in arguments:
        input_folder = arguments['-f']
        sct.check_folder_exist(str(input_folder), verbose=0)
        folder_path = sct.get_absolute_path(input_folder)
    if '-o' in arguments:
        output_folder = arguments['-o']
        if not sct.check_folder_exist(output_folder, verbose=0):
            os.makedirs(str(output_folder))
        output_folder_path = str(output_folder) + "/"
    else:
        output_folder_path = ''
    if '-all-slices' in arguments:
        all_slices = int(arguments['-all-slices'])
    if '-center-seg' in arguments:
        center_seg = int(arguments['-center-seg'])

    # create a folder with all the images
    list_data = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.endswith('.nii.gz') and file.find('_seg') == -1:
                pos_t2 = file.find('_t2')
                subject_name, end_name = file[0:pos_t2 + 3], file[pos_t2 + 3:]
                file_seg = subject_name + '_seg' + end_name
                list_data.append(file)
                list_data.append(file_seg)

    from multiprocessing import Pool
    # crop and slice all these images
    if all_slices == 1:
        arguments = [(folder_path + '/' + str(list_data[iter * 2]), folder_path + '/' + str(list_data[iter * 2 + 1]), v) for iter in range(0,len(list_data) / 2 - 1)]
        if cpu_number != 0:
            pool = Pool(cpu_number)
            pool.map(worker_resized_and_crop, arguments)
            pool.close()
        else:
            for i in range(0, len(list_data/2)):
                worker_resized_and_crop(folder_path + '/' + str(list_data[iter * 2]), folder_path + '/' + str(list_data[iter * 2 + 1]), v)

        for iter in range(0,len(list_data) / 2 - 1):
            path, file, ext = sct.extract_fname(folder_path + '/' + str(list_data[iter * 2]))
            # change the orientation to RPI
            from sct_image import get_orientation_3d
            if not get_orientation_3d(Image(folder_path + '/' + str(list_data[iter * 2]))) == 'RPI':
                sct.run("sct_image -i " + folder_path + '/' + str(list_data[iter * 2]) + " -setorient RPI -o " + folder_path + '/' + str(list_data[iter * 2]), verbose=v)
                sct.run("sct_image -i " + folder_path + '/' + str(list_data[iter * 2 + 1]) + " -setorient RPI -o " + folder_path + '/' + str(list_data[iter * 2 + 1]), verbose=v)

            # get the number of the slice in the source image and crop it
            if not sct.check_folder_exist("Slices_" + file, verbose = 0):
                os.makedirs("Slices_" + file)

            nx, ny, nz, nt, px, py, pz, pt = Image(folder_path + '/' + str(list_data[iter * 2])).dim
            list_random = []
            for i in range(0,10):
                index_random = random.randrange(1,nz)
                list_random.append(index_random)
            arguments = [(folder_path + '/' + str(list_data[iter * 2]), folder_path + '/' + str(list_data[iter * 2 + 1]), fname_size_x, fname_size_y, v, i, center_seg) for i in range(1,nz)]
            if cpu_number != 0:
                try:
                    pool = Pool(cpu_number)
                    pool.map(worker_slice_and_crop, arguments)
                    pool.close()
                except KeyboardInterrupt:
                    print "\nWarning: Caught KeyboardInterrupt, terminating workers"
                    pool.terminate()
                    sys.exit(2)
                except Exception as e:
                    print "Error during straightening on line {}".format(sys.exc_info()[-1].tb_lineno)
                    print e
                    sys.exit(2)
            else:
                for i in range(1, nz):
                    worker_slice_and_crop(folder_path + '/' + str(list_data[iter * 2]), folder_path + '/' + str(list_data[iter * 2 + 1]), fname_size_x, fname_size_y, v, i, center_seg)

    # choose randomly a source and a destination
    fname_src = []
    fname_src_seg =[]
    fname_dest = []
    fname_dest_seg = []
    fname_im = []
    fname_im_seg = []

    if '-i' in arguments:
        fname_src[0] = arguments['-i']
        fname_src_seg[0] = arguments['-iseg']
    else:
        start_time = time.time()
        fname_src, fname_src_seg = random_list(folder_path, list_data, nbre_wrap)
        if verbose:
            elapsed_time = time.time() - start_time
            sct.printv('\nElapsed time to create a random list of source image: ' + str(int(round(elapsed_time))) + 's')
    if '-d' in arguments:
        fname_dest[0] = arguments['-d']
        fname_dest_seg[0] = arguments['-dseg']
    else:
        start_time = time.time()
        fname_dest, fname_dest_seg = random_list(folder_path, list_data, nbre_wrap)
        if verbose:
            elapsed_time = time.time() - start_time
            sct.printv('\nElapsed time to create a random list of destination image: ' + str(int(round(elapsed_time))) + 's')
    if '-t' in arguments:
        fname_im[0] = arguments['-t']
        fname_im_seg[0] = arguments['-tseg']
    else:
        start_time = time.time()
        fname_im, fname_im_seg = random_list(folder_path, list_data, nbre_slice * nbre_wrap)
        if verbose:
            elapsed_time = time.time() - start_time
            sct.printv('\nElapsed time to create a random list of image to tranform: ' + str(int(round(elapsed_time))) + 's')


    # resample data to 1x1x1 mm^3 and crop them along the segmentation
    start_time = time.time()
    arguments_src = [(fname_src[iter], fname_src_seg[iter], v) for iter in range(0, nbre_wrap)]
    arguments_dest = [(fname_dest[iter], fname_dest_seg[iter], v) for iter in range(0, nbre_wrap)]
    arguments_im = [(fname_im[iter], fname_im_seg[iter], v) for iter in range(0, nbre_wrap*nbre_slice)]
    if cpu_number != 0:
        pool = Pool(cpu_number)
        pool.map_async(worker_resized_and_crop, arguments_src)
        pool.map_async(worker_resized_and_crop, arguments_dest)
        pool.map_async(worker_resized_and_crop, arguments_im)
        pool.close()
    else:
        for iter in range(0, nbre_wrap):
            arguments_src = (fname_src[iter], fname_src_seg[iter], v)
            worker_resized_and_crop(arguments_src)
            arguments_dest = (fname_src[iter], fname_src_seg[iter], v)
            worker_resized_and_crop(arguments_dest)
        for iter in range(0, nbre_wrap*nbre_slice):
            arguments_im = (fname_im[iter], fname_im_seg[iter], v)
            worker_resized_and_crop(arguments_im)
    if verbose :
        elapsed_time = time.time() - start_time
        sct.printv('\nElapsed time to crop these images and resized them: ' + str(int(round(elapsed_time))) + 's')

    # choose a random slice in each source image
    start_time = time.time()
    arguments_slice_src = [(fname_src[iter],fname_src_seg[iter],fname_size_x, fname_size_y, folder_path, v, center_seg) for iter in range(0, nbre_wrap)]
    arguments_slice_dest = [(fname_dest[iter], fname_dest_seg[iter], fname_size_x, fname_size_y, folder_path, v, center_seg) for iter in range(0, nbre_wrap)]
    arguments_slice_im = [(fname_im[iter], fname_im_seg[iter], fname_size_x, fname_size_y, folder_path, v, center_seg) for iter in range(0, (nbre_wrap*nbre_slice))]
    if cpu_number != 0:
        pool = Pool(cpu_number)
        r1 = pool.map_async(worker_random_slice, arguments_slice_src)
        r2 = pool.map_async(worker_random_slice, arguments_slice_dest)
        r3 = pool.map_async(worker_random_slice, arguments_slice_im)
        try:
            pool.close()
            pool.join()  # waiting for all the jobs to be done
            src, src_seg, nbre_src = worker_result(r1)
            dest, dest_seg, nbre_dest = worker_result(r2)
            im, im_seg, nbre_im = worker_result(r3)
        except KeyboardInterrupt:
            print "\nWarning: Caught KeyboardInterrupt, terminating workers"
            pool.terminate()
            sys.exit(2)
        except Exception as e:
            print "Error during straightening on line {}".format(sys.exc_info()[-1].tb_lineno)
            print e
            sys.exit(2)
    else:
        src, src_seg, nbre_src = random_slice(fname_src,fname_src_seg, fname_size_x, fname_size_y, folder_path, nbre_wrap, v, center_seg)
        dest, dest_seg, nbre_dest = random_slice(fname_dest, fname_dest_seg, fname_size_x, fname_size_y, folder_path, nbre_wrap, v, center_seg)
        im, im_seg, nbre_im = random_slice(fname_im, fname_im_seg, fname_size_x, fname_size_y, folder_path, nbre_wrap*nbre_slice, v, center_seg)

    if verbose :
        elapsed_time = time.time() - start_time
        sct.printv('\nElapsed time to create a random lists of images: ' + str(int(round(elapsed_time))) + 's')

    # create warping fields beetween source and destination images
    start_time = time.time()
    arguments = [(src_seg[iter], dest_seg[iter], v, iter) for iter in range(0,nbre_wrap)]
    if cpu_number != 0:
        pool = Pool(cpu_number)
        r=pool.map_async(worker_warping_field, arguments)
        try:
            pool.close()
            pool.join()
            warp = worker_warping_result(r)
        except KeyboardInterrupt:
            print "\nWarning: Caught KeyboardInterrupt, terminating workers"
            pool.terminate()
            sys.exit(2)
        except Exception as e:
            print "Error during straightening on line {}".format(sys.exc_info()[-1].tb_lineno)
            print e
            sys.exit(2)
    else:
        warp = warping_field(src_seg, dest_seg, nbre_wrap, v)
    if verbose :
        elapsed_time = time.time() - start_time
        sct.printv('\nElapsed time to create a list of warping field: ' + str(int(round(elapsed_time))) + 's')

    # Apply warping fields to random images
    start_time = time.time()
    arguments = [(im, im_seg, src[iter], nbre_src[iter], dest[iter], nbre_dest[iter], nbre_slice, nbre_wrap, output_folder_path, warp[iter], nbre_im, iter*nbre_slice, v) for iter in range(0, nbre_wrap)]
    if cpu_number !=0:
        pool = Pool(cpu_number)
        pool.map(worker_apply_warping_field, arguments)
        pool.close()
        pool.join()
    else:
        apply_warping_field(im, im_seg, src, dest, nbre_slice, nbre_wrap, output_folder_path, warp, nbre_im, v)

    if verbose :
        elapsed_time = time.time() - start_time
        sct.printv('\nElapsed time to apply the warping field to random images: ' + str(int(round(elapsed_time))) + 's')

    # Delete warping files
    for iter in range(0, nbre_wrap):
        sct.run('rm -rf ' + warp[iter] , verbose=v)
        sct.run('rm -rf ' + str(iter) + '0InverseWarp.nii.gz', verbose=v)

    # Total time
    if verbose :
        elapsed_time = time.time() - start_time_total
        sct.printv('\nFinished! Elapsed time: ' + str(int(round(elapsed_time))) + 's')


# Return a list of random images and segmentation of a given folder
# ==========================================================================================
def random_list(folder_path, list_data, nw):
    list=[]
    list_seg=[]

    for iter in range(0,nw):
        random_index = random.randrange(0,len(list_data) / 2 )
        fname_src = folder_path + '/' + str(list_data[random_index * 2])
        fname_src_seg = folder_path + '/' + str(list_data[random_index * 2 + 1])
        list.append(fname_src)
        list_seg.append(fname_src_seg)

    return list, list_seg


# Crop the image to stay in the boundaries of the segmentation
# ==========================================================================================
def crop_segmentation(fname, fname_seg, v):

    path, file, ext = sct.extract_fname(fname)
    if not sct.check_folder_exist("Slices_" + file, verbose = 0):
        nx, ny, nz, nt, px, py, pz, pt = Image(fname_seg).dim

        data_seg = Image(fname_seg).data
        i = 1
        while np.all(data_seg[:, :, i] == np.zeros((nx,ny))):
            i += 1
        i += 0.15*nz
        j = nz -1
        while np.all(data_seg[:, :, j] == np.zeros((nx,ny))):
            j -= 1
        j -= 0.1*nz

        sct.run("sct_crop_image -i " + fname + " -dim 2 -start " + str(i) + " -end " + str(j) + " -o " + fname, verbose= v )
        sct.run("sct_crop_image -i " + fname_seg + " -dim 2 -start " + str(i) + " -end " + str(j) + " -o " + fname_seg, verbose= v )


# Resized and crop the image
# ==========================================================================================
def worker_resized_and_crop(argument):

    fname, fname_seg, v = argument
    # resample data to 1x1x1 mm^3
    try:
        nx, ny, nz, nt, px, py, pz, pt = Image(fname).dim
        if not (px == 1 and py == 1 and pz ==1):
            sct.run('sct_resample -i ' + fname + ' -mm 1x1x1 -x nn -o ' + fname, verbose=v)
            sct.run('sct_resample -i ' + fname_seg + ' -mm 1x1x1 -x nn -o ' + fname_seg, verbose=v)
            # change the orientation to RPI
        from sct_image import get_orientation_3d
        if not get_orientation_3d(Image(fname)) == 'RPI':
            sct.run("sct_image -i " + fname + " -setorient RPI -o " + fname, verbose=v)
            sct.run("sct_image -i " + fname_seg + " -setorient RPI -o " + fname_seg, verbose=v)
        # crop_segmentation(fname, fname_seg, v)
    except KeyboardInterrupt:
        return
    except Exception as e:
        raise e


# Crop the image along z, centered  it and crop it along the two others dimensions with a given size
# ==========================================================================================
def worker_slice_and_crop(argument):
    fname, fname_seg, fname_size_x, fname_size_y, v, nbre, center_seg = argument

    try:
        from msct_image import crop_x_y
        # extract path file and extension
        path, file, ext = sct.extract_fname(fname)
        current_path = os.getcwd()

        # crop the image along the z dimension
        sct.run("sct_crop_image -i " + fname + " -dim 2 -start " + str(nbre) + " -end " + str(nbre) + " -o " + current_path + '/' + "Slices_" + file + '/' +file + "_slice_" + str(nbre) + ".nii.gz", verbose=v)
        sct.run("sct_crop_image -i " + fname_seg + " -dim 2 -start " + str(nbre) + " -end " + str(nbre) + " -o " + current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(nbre) + "_seg.nii.gz", verbose=v)

        fname_slice = current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(nbre) + ".nii.gz"
        fname_slice_seg = current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(nbre) + "_seg.nii.gz"

        output_slice = current_path + '/' + "Slices_" + file + '/' + file + "_crop_" + str(nbre) + "_o0.nii.gz"
        output_seg = current_path + '/' + "Slices_" + file + '/' + file + "_crop_" + str(nbre) + "_seg_o0.nii.gz"
        crop_x_y(fname_slice,fname_slice_seg, fname_size_x, fname_size_y, output_slice, output_seg, center_seg)

    except KeyboardInterrupt:
        return
    except Exception as e:
        raise e


# Get random slices and their place in a given image
# ==========================================================================================
def worker_random_slice(arguments_worker):

    from msct_image import crop_x_y
    fname, fname_seg, fname_size_x, fname_size_y, folder_path, v, center_seg = arguments_worker
    try:
        path, file, ext = sct.extract_fname(fname)
        path_seg, file_seg, ext_seg = sct.extract_fname(fname_seg)

        # get the number of the slice in the source image and crop it
        if not sct.check_folder_exist("Slices_" + file, verbose=0):
            os.makedirs("Slices_" + file)
        nx, ny, nz, nt, px, py, pz, pt = Image(fname).dim
        nbre_im = random.randrange(1, nz - 1)
        im = "Slices_" + file + '/' + file + "_crop_" + str(nbre_im) + "_o0.nii.gz"
        if not os.path.isfile(im):
            current_path = os.getcwd()
            slice_z = nbre_im
            # crop the image along the z dimension
            sct.run("sct_crop_image -i " + folder_path + '/' + file + ext + " -dim 2 -start " + str(slice_z) + " -end " + str(slice_z) + " -o " + current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + ".nii.gz", verbose=v)
            sct.run("sct_crop_image -i " + folder_path + '/' + file_seg + ext_seg + " -dim 2 -start " + str(slice_z) + " -end " + str(slice_z) + " -o " + current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + "_seg.nii.gz",verbose=v)

            from numpy import asarray
            fname_slice = current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + ".nii.gz"
            fname_slice_seg = current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + "_seg.nii.gz"
            output_slice = current_path + '/' + "Slices_" + file + '/' + file + "_crop_" + str(slice_z) + "_o0" + ".nii.gz"
            output_seg = current_path + '/' + "Slices_" + file + '/' + file + "_crop_" + str(slice_z) + "_seg_o0" + ".nii.gz"
            crop_x_y(fname_slice, fname_slice_seg, fname_size_x, fname_size_y, output_slice, output_seg, center_seg)

        im = "Slices_" + file + '/'+ file + "_crop_" + str(nbre_im) + "_o0.nii.gz"
        im_seg = "Slices_" + file + '/'+ file + "_crop_" + str(nbre_im) + "_seg_o0.nii.gz"
        return im, im_seg, nbre_im
    except KeyboardInterrupt:
        return

    except Exception as e:
        raise e


# Get random slices and their place in a given image
# ==========================================================================================
def random_slice(fname, fname_seg, fname_size_x, fname_size_y, folder_path,nbre_wrap, v, center_seg):

    from msct_image import crop_x_y
    im_list = [] ; im_seg_list = [] ; nbre_im_list = []
    for iter in range(0, nbre_wrap):
        path, file, ext = sct.extract_fname(fname[iter])
        path_seg, file_seg, ext_seg = sct.extract_fname(fname_seg[iter])

        # change the orientation to RPI
        from sct_image import get_orientation_3d
        if not get_orientation_3d(Image(fname[iter])) == 'RPI':
            sct.run("sct_image -i " + fname[iter] + " -setorient RPI -o " + fname[iter], verbose=v)
            sct.run("sct_image -i " + fname_seg[iter] + " -setorient RPI -o " + fname_seg[iter], verbose=v)

        # get the number of the slice in the source image and crop it
        if not sct.check_folder_exist("Slices_" + file, verbose = 0):
            os.makedirs("Slices_" + file)
        nx, ny, nz, nt, px, py, pz, pt = Image(fname[iter]).dim
        nbre = random.randrange(1, nz - 1)
        im = "Slices_" + file + '/' + file + "_crop_" + str(nbre) + "_o0.nii.gz"
        if not os.path.isfile(im):
            current_path = os.getcwd()
            slice_z = nbre
            # crop the image along the z dimension
            sct.run("sct_crop_image -i " + folder_path + '/' + file + ext + " -dim 2 -start " + str(slice_z) + " -end " + str(slice_z) + " -o " + current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + ".nii.gz", verbose=v)
            sct.run("sct_crop_image -i " + folder_path + '/' + file_seg + ext_seg + " -dim 2 -start " + str(slice_z) + " -end " + str(slice_z) + " -o " + current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + "_seg.nii.gz", verbose=v)

            from numpy import asarray
            fname_slice = current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + ".nii.gz"
            fname_slice_seg = current_path + '/' + "Slices_" + file + '/' + file + "_slice_" + str(slice_z) + "_seg.nii.gz"
            output_slice = current_path + '/' + "Slices_" + file + '/' + file + "_crop_" + str(slice_z) + "_o0" + ".nii.gz"
            output_seg = current_path + '/' + "Slices_" + file + '/' + file + "_crop_" + str(slice_z) + "_seg_o0" + ".nii.gz"
            crop_x_y(fname_slice, fname_slice_seg, fname_size_x, fname_size_y, output_slice, output_seg, center_seg)

        im = "Slices_" + file + '/' + file + "_crop_" + str(nbre) + "_o0.nii.gz"
        im_seg = "Slices_" + file + '/' + file + "_crop_" + str(nbre) + "_seg_o0.nii.gz"

        im_list.append(im)
        im_seg_list.append(im_seg)
        nbre_im_list.append(nbre)

    return im_list, im_seg_list, nbre_im_list


# callback function of the random slice worker
# ==========================================================================================
def worker_result(results):
    im_list = [] ; im_seg_list = [] ; nbre_im_list = []
    for im, im_seg, nbre_im in results.get():
        im_list.append(im)
        im_seg_list.append(im_seg)
        nbre_im_list.append(nbre_im)
    return im_list, im_seg_list, nbre_im_list


# Create warping field
# ==========================================================================================
def warping_field(src_seg, dest_seg, nw, v):
    warp = []
    for iter in range(0, nw):

        out = "t2_output_image_transformed.nii.gz"
        out_transfo = str(iter)

        sct.run('isct_antsRegistration ' +
                '--dimensionality 2 ' +
                '--transform BSplineSyN[0.5,1,3] ' +
                '--metric MeanSquares[' + dest_seg[iter] + ',' + src_seg[iter] + ', 1] ' +
                '--convergence 5x3 ' +
                '--shrink-factors 2x1 ' +
                '--smoothing-sigmas 1x0mm ' +
                '--output [' + out_transfo + ',' + out + '] ' +
                '--interpolation BSpline[3] ' +
                '--verbose 0', verbose = v)

        warp.append(out_transfo + '0Warp.nii.gz')
    return warp


# Create warping field (multiprocess)
# ==========================================================================================
def worker_warping_field(argument):
    src_seg, dest_seg, v, iter = argument

    out = "t2_output_image_transformed.nii.gz"
    out_transfo = str(iter)

    sct.run('isct_antsRegistration ' +
            '--dimensionality 2 ' +
            '--transform BSplineSyN[0.5,1,3] ' +
            '--metric MeanSquares[' + dest_seg + ',' + src_seg + ', 1] ' +
            '--convergence 5x3 ' +
            '--shrink-factors 2x1 ' +
            '--smoothing-sigmas 1x0mm ' +
            '--output [' + out_transfo + ',' + out + '] ' +
            '--interpolation BSpline[3] ' +
            '--verbose 0', verbose=v)

    warp = out_transfo + '0Warp.nii.gz'
    return warp


# callback function of the random slice worker
# ==========================================================================================
def worker_warping_result(results):
    warp = []
    for r in results.get():
        warp.append(r)
    return warp


# Apply warping field
# ==========================================================================================
def apply_warping_field(im, im_seg, src, dest, nbre_slice, nbre_wrap,  output_folder_path, wrap, nbre_im, v):
    j=0
    for i in range(0, nbre_wrap):
        src_path, src_file, src_ext = sct.extract_fname(src[i])
        dest_path, dest_file, dest_ext = sct.extract_fname(dest[i])
        for iter in range(0, nbre_slice):
            fname_out_im = 'transfo_' + src_file + '_' + dest_file + '_' + str(nbre_im[j]) + '.nii.gz'
            fname_out_seg = "transfo_" + src_file + '_' + dest_file + '_' + str(nbre_im[j]) + '_seg.nii.gz'
            # Apply warping field to src data
            sct.run('isct_antsApplyTransforms -d 2 -i ' + im[j] + ' -r ' + dest[i] + ' -n NearestNeighbor -t ' + wrap[i] + ' --output ' + output_folder_path + fname_out_im, verbose=v)
            sct.run('isct_antsApplyTransforms -d 2 -i ' + im_seg[j] + ' -r ' + dest[i] + ' -n NearestNeighbor -t ' + wrap[i] + ' --output ' + output_folder_path  + fname_out_seg, verbose=v)
            j += 1


# Apply warping field
# ==========================================================================================
def worker_apply_warping_field(argument):
    im, im_seg, src, nbre_src, dest, nbre_dest, nbre_slice, nbre_wrap, output_folder_path, wrap, nbre_im, j, v = argument

    src_path, src_file, src_ext = sct.extract_fname(src)
    pos_crop_src = src_file.find('_crop')
    dest_path, dest_file, dest_ext = sct.extract_fname(dest)
    pos_crop_dest = dest_file.find('_crop')
    for iter in range(0, nbre_slice):
        im_path, im_file, im_ext = sct.extract_fname(im[j+iter])
        pos_crop_im = im_file.find('_crop')
        fname_out_im = src_file[:pos_crop_src] + str(nbre_src) + '_' + dest_file[:pos_crop_dest] + str(nbre_dest) + '_' + im_file[:pos_crop_im] + str(nbre_im[j+iter]) + '.nii.gz'
        fname_out_seg = src_file[:pos_crop_src] + str(nbre_src) + '_' + dest_file[:pos_crop_dest] + str(nbre_dest) + '_' + im_file[:pos_crop_im] + str(nbre_im[j+iter]) + '_seg.nii.gz'
        # Apply warping field to src data
        sct.run('isct_antsApplyTransforms -d 2 -i ' + im[j+iter] + ' -r ' + dest + ' -n NearestNeighbor -t ' + wrap + ' --output ' + output_folder_path + fname_out_im, verbose=v)
        sct.run('isct_antsApplyTransforms -d 2 -i ' + im_seg[j+iter] + ' -r ' + dest + ' -n NearestNeighbor -t ' + wrap + ' --output ' + output_folder_path + fname_out_seg, verbose=v)


# START PROGRAM
# ==========================================================================================
if __name__ == "__main__":
    # call main function
    main()