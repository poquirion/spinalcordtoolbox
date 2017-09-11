#!/usr/bin/env python
#
# Test major functions.
#
# Authors: Julien Cohen-Adad, Benjamin De Leener, Augustin Roux
# Updated: 2014-10-06

# TODO: list functions to test in help (do a search in testing folder)


import sys
import time, random
from copy import deepcopy
import os
from pandas import DataFrame
from msct_parser import Parser

# get path of the toolbox
# TODO: put it back below when working again (julien 2016-04-04)
# <<<
# OLD
# status, path_sct = commands.getstatusoutput('echo $SCT_DIR')
# NEW
path_script = os.path.dirname(__file__)
path_sct = os.path.dirname(path_script)
# >>>
# append path that contains scripts, to be able to load modules
sys.path.append(path_sct + '/scripts')
sys.path.append(path_sct + '/testing')
import sct_utils as sct
import importlib

# define nice colors


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

# JULIEN: NOW THAT THE USER WILL HAVE ACCESS TO TEST_ALL, WE SHOULD NOT USE $SCT_TESTING_DATA_DIR ANYMORE.
# get path of testing data
# status, path_sct_testing = commands.getstatusoutput('echo $SCT_TESTING_DATA_DIR')


class Param:
    def __init__(self):
        self.download = 0
        self.path_data = 'sct_testing_data/'  # path to the testing data
        self.function_to_test = None
        # self.function_to_avoid = None
        self.remove_tmp_file = 0
        self.verbose = 1
        # self.url_git = 'https://github.com/neuropoly/sct_testing_data.git'
        self.path_tmp = ''
        self.args = ''  # input arguments to the function
        self.contrast = ''  # folder containing the data and corresponding to the contrast. Could be t2, t1, t2s, etc.
        self.output = ''  # output string coded into DataFrame
        self.redirect_stdout = 1  # for debugging, set to 0. Otherwise set to 1.


# START MAIN
# ==========================================================================================
def main(args=None):
    if args is None:
        args = sys.argv[1:]

    # get parser
    parser = get_parser()
    arguments = parser.parse(args)

    if '-d' in arguments:
        param.download = int(arguments['-d'])
    if '-p' in arguments:
        param.path_data = arguments['-p']
    if '-f' in arguments:
        param.function_to_test = arguments['-f']
    if '-r' in arguments:
        param.remove_tmp_file = int(arguments['-r'])

    # path_data = param.path_data
    function_to_test = param.function_to_test

    start_time = time.time()

    # get absolute path and add slash at the end
    param.path_data = sct.slash_at_the_end(os.path.abspath(param.path_data), 1)

    # check existence of testing data folder
    if not os.path.isdir(param.path_data) or param.download:
        downloaddata()

    # display path to data
    sct.printv('\nPath to testing data: ' + param.path_data, param.verbose)

    # create temp folder that will have all results and go in it
    param.path_tmp = sct.tmp_create()
    os.chdir(param.path_tmp)

    # get list of all scripts to test
    functions = fill_functions()
    if function_to_test:
        if not function_to_test in functions:
            sct.printv('ERROR: Function "%s" is not part of the list of testing functions' % function_to_test, type='error')
        # loop across all functions and test them
        status = [test_function(f) for f in functions if function_to_test == f]
    else:
        status = [test_function(f) for f in functions]
    print 'status: ' + str(status)

    # display elapsed time
    elapsed_time = time.time() - start_time
    print 'Finished! Elapsed time: ' + str(int(round(elapsed_time))) + 's\n'

    # remove temp files
    if param.remove_tmp_file:
        sct.printv('\nRemove temporary files...', param.verbose)
        sct.run('rm -rf ' + param.path_tmp, param.verbose)

    e = 0
    if sum(status) != 0:
        e = 1
    print e

    sys.exit(e)


def downloaddata():
    sct.printv('\nDownloading testing data...', param.verbose)
    import sct_download_data
    sct_download_data.main(['-d', 'sct_testing_data'])
    # sct.run('sct_download_data -d sct_testing_data')


# list of all functions to test
# ==========================================================================================
def fill_functions():
    functions = [
        'sct_analyze_texture',
        'sct_apply_transfo',
        # 'sct_check_atlas_integrity',
        'sct_compute_mtr',
        'sct_concat_transfo',
        'sct_convert',
        # 'sct_convert_binary_to_trilinear',  # not useful
        'sct_create_mask',
        'sct_crop_image',
        'sct_dmri_compute_dti',
        'sct_dmri_create_noisemask',
        'sct_dmri_get_bvalue',
        'sct_dmri_transpose_bvecs',
        'sct_dmri_moco',
        'sct_dmri_separate_b0_and_dwi',
        'sct_documentation',
        'sct_extract_metric',
        # 'sct_flatten_sagittal',
        'sct_fmri_compute_tsnr',
        'sct_fmri_moco',
        # 'sct_get_centerline',
        'sct_image',
        'sct_label_utils',
        'sct_label_vertebrae',
        'sct_maths',
        'sct_process_segmentation',
        'sct_propseg',
        'sct_register_graymatter',
        'sct_register_multimodal',
        'sct_register_to_template',
        'sct_resample',
        'sct_segment_graymatter',
        'sct_smooth_spinalcord',
        'sct_straighten_spinalcord',
        'sct_warp_template',
    ]
    return functions


# print without carriage return
# ==========================================================================================
def print_line(string):
    import sys
    sys.stdout.write(string + make_dot_lines(string))
    sys.stdout.flush()


# fill line with dots
# ==========================================================================================
def make_dot_lines(string):
    if len(string) < 52:
        dot_lines = '.' * (52 - len(string))
        return dot_lines
    else:
        return ''


# print in color
# ==========================================================================================
def print_ok():
    print "[" + bcolors.OKGREEN + "OK" + bcolors.ENDC + "]"


def print_warning():
    print "[" + bcolors.WARNING + "WARNING" + bcolors.ENDC + "]"


def print_fail():
    print "[" + bcolors.FAIL + "FAIL" + bcolors.ENDC + "]"


# write to log file
# ==========================================================================================
def write_to_log_file(fname_log, string, mode='w', prepend=False):
    """
    status, output = sct.run('echo $SCT_DIR', 0)
    path_logs_dir = output + '/testing/logs'

    if not os.path.isdir(path_logs_dir):
        os.makedirs(path_logs_dir)
    mode: w: overwrite, a: append, p: prepend
    """
    string_to_append = ''
    string = "test ran at " + time.strftime("%y%m%d%H%M%S") + "\n" \
             + fname_log \
             + string
    # open file
    try:
        # if prepend, read current file and then overwrite
        if prepend:
            f = open(fname_log, 'r')
            # string_to_append = '\n\nOUTPUT:\n--\n' + f.read()
            string_to_append = f.read()
            f.close()
        f = open(fname_log, mode)
    except Exception as ex:
        raise Exception('WARNING: Cannot open log file.')
    f.write(string + string_to_append + '\n')
    f.close()


# test function
# ==========================================================================================
# def test_function(function_to_test):
#     # if script_name == 'test_debug':
#     #     return test_debug()  # JULIEN
#     # else:
#     # build script name
#     fname_log = '../' + function_to_test + '.log'
#     tmp_script_name = function_to_test
#     result_folder = 'results_' + function_to_test
#
#     sct.create_folder(result_folder)
#     os.chdir(result_folder)
#
#     # display script name
#     print_line('Checking ' + function_to_test)
#     # import function as a module
#     script_tested = importlib.import_module('test_' + function_to_test)
#     # test function
#     result_test = script_tested.test(param.path_data)
#     # test functions can return 2 or 3 variables, depending if there is results.
#     # In this script, we look only at the first two variables.
#     status, output = result_test[0], result_test[1]
#     # write log file
#     write_to_log_file(fname_log, output, 'w')
#     # manage status
#     if status == 0:
#         print_ok()
#     else:
#         if status == 99:
#             print_warning()
#         else:
#             print_fail()
#         print output
#     # go back to parent folder
#     os.chdir('..')
#
#     # return
#     return status


# init_testing
# ==========================================================================================
def test_function(param_test):
    """

    Parameters
    ----------
    file_testing

    Returns
    -------
    path_output [str]: path where to output testing data
    """

    # load modules of function to test
    module_function_to_test = importlib.import_module(param_test.function_to_test)
    module_testing = importlib.import_module('test_' + param_test.function_to_test)

    # initialize testing parameters specific to this function
    param_test = module_testing.init(param_test)

    # get parser information
    parser = module_function_to_test.get_parser()
    dict_param = parser.parse(param_test.args.split(), check_file_exist=False)
    dict_param_with_path = parser.add_path_to_file(deepcopy(dict_param), param_test.path_data, input_file=True)
    param_test.param_with_path = parser.dictionary_to_string(dict_param_with_path)

    # retrieve subject name
    subject_folder = sct.slash_at_the_end(param_test.path_data, 0).split('/')
    subject_folder = subject_folder[-1]
    # build path_output variable
    param_test.path_output = sct.slash_at_the_end(param_test.function_to_test + '_' + subject_folder + '_' + time.strftime("%y%m%d%H%M%S") + '_' + str(random.randint(1, 1000000)), slash=1)
    param_test.param_with_path += ' -ofolder ' + param_test.path_output
    sct.create_folder(param_test.path_output)

    # log file
    param_test.fname_log = param_test.path_output + param_test.function_to_test + '.log'
    stdout_log = file(param_test.fname_log, 'w')
    # redirect to log file
    param_test.stdout_orig = sys.stdout
    if param_test.redirect_stdout:
        sys.stdout = stdout_log

    # initialize panda dataframe
    param_test.results = DataFrame(index=[param_test.path_data], data={'status': int(0), 'output': param_test.output})

    # retrieve input file (will be used later for integrity testing)
    if '-i' in dict_param:
        param_test.file_input = dict_param['-i'].split('/')[1]

    # Extract contrast
    if '-c' in dict_param:
        param_test.contrast = dict_param['-c']

    # Check if input files exist
    if not (os.path.isfile(dict_param_with_path['-i'])):
        param_test.output += '\nERROR: the file provided to test function does not exist in folder: ' + param_test.path_data
        write_to_log_file(param_test.fname_log, param_test.output, 'w')
        param_test.results = DataFrame(index=[param_test.path_data], data={'status': int(200), 'output': param_test.output})
        return param_test

    # Check if ground truth files exist
    param_test.fname_groundtruth = param_test.path_data + param_test.contrast + '/' + sct.add_suffix(param_test.file_input, param_test.suffix_groundtruth)
    if not os.path.isfile(param_test.fname_groundtruth):
        param_test.output += '\nERROR: the file *_labeled_center_manual.nii.gz does not exist in folder: ' + param_test.fname_groundtruth
        write_to_log_file(param_test.fname_log, param_test.output, 'w')
        param_test.results = DataFrame(index=[param_test.path_data], data={'status': int(201), 'output': param_test.output})
        return param_test

    # run command
    cmd = param_test.function_to_test + param_test.param_with_path
    param_test.output += '\n====================================================================================================\n' + cmd + '\n====================================================================================================\n\n'  # copy command
    time_start = time.time()
    try:
        param_test.status, o = sct.run(cmd, 0)
    except:
        param_test.output += 'ERROR: Function crashed!'
        write_to_log_file(param_test.fname_log, param_test.output, 'w')
        param_test.results = DataFrame(index=[param_test.path_data], data={'status': int(1), 'output': param_test.output})
        return param_test


    param_test.output += o
    param_test.duration = time.time() - time_start

    # test integrity
    param_test.output += '\n\n====================================================================================================\n' + 'INTEGRITY TESTING' + '\n====================================================================================================\n\n'  # copy command
    try:
        param_test = module_testing.test_integrity(param_test)
    except:
        param_test.output += 'ERROR: Integrity testing crashed!'
        write_to_log_file(param_test.fname_log, param_test.output, 'w')
        param_test.results = DataFrame(index=[param_test.path_data], data={'status': int(2), 'output': param_test.output})
        return param_test

    # manage stdout
    if param_test.redirect_stdout:
        sys.stdout.close()
        sys.stdout = param_test.stdout_orig
    # write log file
    write_to_log_file(param_test.fname_log, param_test.output, mode='r+', prepend=True)

    return param_test


def get_parser():
    # Initialize the parser
    parser = Parser(__file__)
    parser.usage.set_description('Crash and integrity testing for functions of the Spinal Cord Toolbox. Internet connection is required for downloading testing data.')
    parser.add_option(name="-f",
                      type_value="str",
                      description="Test this specific script (do not add extension).",
                      mandatory=False,
                      example='sct_propseg')
    parser.add_option(name="-d",
                      type_value="multiple_choice",
                      description="Download testing data.",
                      mandatory=False,
                      default_value=param.download,
                      example=['0', '1'])
    parser.add_option(name="-p",
                      type_value="folder",
                      description='Path to testing data. NB: no need to set if using "-d 1"',
                      mandatory=False,
                      default_value=param.path_data)
    parser.add_option(name="-r",
                      type_value="multiple_choice",
                      description='Remove temporary files.',
                      mandatory=False,
                      default_value='1',
                      example=['0', '1'])
    return parser


if __name__ == "__main__":
    # initialize parameters
    param = param()
    # call main function
    main()
