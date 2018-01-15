#!/usr/bin/env python
# File created on 15 Jan 2017
from __future__ import division

__author__ = "Gavin Douglas"
__copyright__ = "Copyright 2011-2017, The PICRUSt Project"
__credits__ = ["Gavin Douglas", "Morgan Langille"]
__license__ = "GPL"
__version__ = "1.1.3"
__maintainer__ = "Gavin Douglas"
__email__ = "gavinmdouglas@gmail.com"
__status__ = "Development"


from cogent.util.option_parsing import parse_command_line_parameters, make_option
from picrust.wrap_hsp import ace_for_picrust

script_info = {}
script_info['brief_description'] = "Given a tree and a set of known " +\
                                   "character states will output " +\
                                   "predictions for unobserved character " +\
                                   "states. Note this does not require a " +\
                                   "separate ancestral state " +\
                                   "reconstruction step to be run."
script_info['script_description'] =\
"""
This script performs hidden state prediction on tips in the input tree with unknown trait values. 

Typically this script is used to predict the abundance of gene families present in each taxon, given a tree and a set of known trait values.

This script outputs a table of trait predictions.
"""

# Script usage examples from predict_traits.py
#script_info['script_usage'] = [\
#("","Required options with NSTI:","%prog -a -i trait_table.tab -t reference_tree.newick -r asr_counts.tab -o predict_traits.tab"),\
#("","Limit predictions to particular tips in OTU table:","%prog -a -i trait_table.tab -t reference_tree.newick -o predict_traits_limited.tab -l otu_table.tab"),
#("","Reconstruct confidence","%prog -a -i trait_table.tab -t reference_tree.newick  -o predict_traits.tab")
#]

HSP_METHODS = ['emp_prob', 'mk_model', 'mp', 'pic', 'sqp']

# Define command-line interface
script_info['output_description']= "Output is a tab-delimited table of predicted character states"
script_info['required_options'] = [

  make_option('-i', '--observed_trait_table', type="existing_filepath",
              help='the input trait table describing directly observed ' +\
                   'traits (e.g. sequenced genomes) in tab-delimited format'),

  make_option('-t', '--tree', type="existing_filepath",
              help='the full reference tree, in newick format')
]

script_info['optional_options'] = [

  make_option('-o', '--output_trait_table', type="new_filepath",
              default='predicted_traits.tsv',
              help='the output filepath for trait predictions ' +\
                   '[default: %default]'),

  make_option('--ci_out', type="new_filepath",
              default='predicted_traits_ci.tsv',
              help='the output filepath for confidence intervals trait ' +\
                   'predictions (if -c option set) [default: %default]'),

  make_option('-m', '--hsp_method', default='emp_prob', choices=HSP_METHODS,
              help='HSP method to use, options: ' +\
                  ", ".join(HSP_METHODS) + '. "emp_prob": ' +\
                  'predict discrete traits based on empirical state ' +\
                  'probabilities across tips. "mk_model": predict ' +\
                  'discrete traits based on fixed-rates continuous time ' +\
                  'Markov model. "mp": predict discrete traits using max ' +\
                  'parsimony. "pic": predict continuous trait with ' +\
                   'phylogentic independent contrast. "sqp": ' +\
                  'reconstruct continuous traits using squared-change ' +\
                  'parsimony [default: %default]'),

  make_option('-n', '--calculate_NSTI', default=False,
              action="store_true", 
              help='if specified, calculate NSTI and add to output file ' +\
                   '[default: %default]'),

  make_option('-c', "--confidence", default=False, action="store_true", 
              help='if specified, output 95% confidence intervals (only ' +\
                   'possible for mk_model, emp_prob, and mp settings) ' +\
                   '[default: %default]'),

  make_option('--check', default=False, action="store_true", 
              help='if specified, check input trait table before hsp ' +\
                   '[default: %default]'),

  make_option('--no_round', default=False, action="store_true",
              help='Flag to set if you do not want predictions to be ' +\
                   'rounded to the nearest integer (if using continuous ' +\
                   'HSP method) [default: %default]'),

  make_option('--threads', default=1, type="int",
              help='Number of threads to use when running mk_model ' +\
                   '[default: %default]')
]

script_info['version'] = __version__

#Helper formatting functions

def write_results_to_file(f_out,headers,predictions,sep="\t"):
    """Write a set of predictions to a file

    headers -- a list of header columns
    predictions -- a dict of predictions, keyed by organism
    with arrays as values
    """
    f= open(f_out,"w")
    lines = [sep.join(headers)+"\n"]

    for pred in sorted(predictions.keys()):
        new_fields = [pred]
        value = predictions[pred]
        #print value
        if value is None or len(value) == 0:
            continue
        trait_value_fields = list(value)
        new_fields.extend(trait_value_fields)
        #print new_fields
        new_line = sep.join(map(str,new_fields))
        lines.append("%s\n" % new_line)
    f.writelines(lines)
    f.close()


def main():
    option_parser, opts, args =\
       parse_command_line_parameters(**script_info)

    #if we specify we want NSTI only then we have to calculate it first
    if opts.output_accuracy_metrics_only:
        opts.calculate_accuracy_metrics=True

    if opts.verbose:
        print "Loading tree from file:", opts.tree

    if opts.no_round:
        round_opt = False 
    else:
        round_opt = True

    # Load Tree
    tree = load_picrust_tree(opts.tree, opts.verbose)

    table_headers=[]
    traits={}
    #load the asr trait table using the previous list of functions to order the arrays
    if opts.reconstructed_trait_table:
        table_headers,traits =\
                update_trait_dict_from_file(opts.reconstructed_trait_table)

        #Only load confidence intervals on the reconstruction
        #If we actually have ASR values in the analysis
        if opts.reconstruction_confidence:
            if opts.verbose:
                print "Loading ASR confidence data from file:",\
                opts.reconstruction_confidence
                print "Assuming confidence data is of type:",opts.confidence_format

            asr_confidence_output = open(opts.reconstruction_confidence)
            asr_min_vals,asr_max_vals, params,column_mapping =\
              parse_asr_confidence_output(asr_confidence_output,format=opts.confidence_format)
            if 'sigma' in params:
                brownian_motion_parameter = params['sigma'][0]
            else:
                brownian_motion_parameter = None

            if opts.verbose:
                print "Done. Loaded %i confidence interval values." %(len(asr_max_vals))
                print "Brownian motion parameter:",brownian_motion_parameter
        else:
            brownian_motion_parameter = None

    #load the trait table into a dict with organism names as keys and arrays as functions
    table_headers,genome_traits =\
            update_trait_dict_from_file(opts.observed_trait_table,table_headers)


    #Combine the trait tables overwriting the asr ones if they exist in the genome trait table.
    traits.update(genome_traits)

    # Specify the attribute where we'll store the reconstructions
    trait_label = "Reconstruction"

    if opts.verbose:
        print "Assigning traits to tree..."

    # Decorate tree using the traits
    tree = assign_traits_to_tree(traits,tree, trait_label=trait_label)


    if opts.reconstruction_confidence:
        if opts.verbose:
            print "Assigning trait confidence intervals to tree..."
        tree = assign_traits_to_tree(asr_min_vals,tree,\
            trait_label="lower_bound")

        tree = assign_traits_to_tree(asr_max_vals,tree,\
            trait_label="upper_bound")

        if brownian_motion_parameter is None:

             if opts.verbose:
                 print "No Brownian motion parameters loaded. Inferring these from 95% confidence intervals..."
             brownian_motion_parameter = get_brownian_motion_param_from_confidence_intervals(tree,\
                      upper_bound_trait_label="upper_bound",\
                      lower_bound_trait_label="lower_bound",\
                      trait_label=trait_label,\
                      confidence=0.95)
             if opts.verbose:
                 print "Inferred the following rate parameters:",brownian_motion_parameter
    if opts.verbose:
        print "Collecting list of nodes to predict..."

    #Start by predict all tip nodes.
    nodes_to_predict = [tip.Name for tip in tree.tips()]

    if opts.verbose:
        print "Found %i nodes to predict." % len(nodes_to_predict)

    if opts.limit_predictions_to_organisms:
        organism_id_str = opts.limit_predictions_to_organisms
        ok_organism_ids = organism_id_str.split(',')
        ok_organism_ids = [n.strip() for n in ok_organism_ids]
        for f in set_label_conversion_fns(True,True):
            ok_organism_ids = [f(i) for i in ok_organism_ids]

        if opts.verbose:
            print "Limiting predictions to user-specified ids:",\
              ",".join(ok_organism_ids)


        if not ok_organism_ids:
            raise RuntimeError(\
              "Found no valid ids in input: %s. Were comma-separated ids specified on the command line?"\
              % opts.limit_predictions_to_organisms)

        nodes_to_predict =\
          [n for n in nodes_to_predict if n in ok_organism_ids]

        if not nodes_to_predict:
            raise RuntimeError(\
              "Filtering by user-specified ids resulted in an empty set of nodes to predict.   Are the ids on the commmand-line and tree ids in the same format?  Example tree tip name: %s, example OTU id name: %s" %([tip.Name for tip in tree.tips()][0],ok_organism_ids[0]))

        if opts.verbose:
            print "After filtering organisms to predict by the ids specified on the commandline, %i nodes remain to be predicted" %(len(nodes_to_predict))

    if opts.limit_predictions_by_otu_table:
        if opts.verbose:
            print "Limiting predictions to ids in user-specified OTU table:",\
              opts.limit_predictions_by_otu_table
        otu_table = open(opts.limit_predictions_by_otu_table,"U")
        #Parse OTU table for ids

        otu_ids =\
          extract_ids_from_table(otu_table.readlines(),delimiter="\t")

        if not otu_ids:
            raise RuntimeError(\
              "Found no valid ids in input OTU table: %s.  Is the path correct?"\
              % opts.limit_predictions_by_otu_table)

        nodes_to_predict =\
          [n for n in nodes_to_predict if n in otu_ids]

        if not nodes_to_predict:
            raise RuntimeError(\
              "Filtering by OTU table resulted in an empty set of nodes to predict.   Are the OTU ids and tree ids in the same format?  Example tree tip name: %s, example OTU id name: %s" %([tip.Name for tip in tree.tips()][0],otu_ids[0]))

        if opts.verbose:
            print "After filtering by OTU table, %i nodes remain to be predicted" %(len(nodes_to_predict))

    # Calculate accuracy of PICRUST for the given tree, sequenced genomes
    # and set of ndoes to predict
    accuracy_metrics = ['NSTI']
    accuracy_metric_results = None
    if opts.calculate_accuracy_metrics:
        if opts.verbose:
            print "Calculating accuracy metrics: %s" %([",".join(accuracy_metrics)])
        accuracy_metric_results = {}
        if 'NSTI' in accuracy_metrics:

            nsti_result,min_distances =\
                calc_nearest_sequenced_taxon_index(tree,\
                limit_to_tips = nodes_to_predict,\
                trait_label = trait_label, verbose=opts.verbose)

            #accuracy_metric_results['NSTI'] = nsti_result
            for organism in min_distances.keys():
                accuracy_metric_results[organism] = {'NSTI': min_distances[organism]}

            if opts.verbose:
                print "NSTI:", nsti_result

        if opts.output_accuracy_metrics_only:
            #Write accuracy metrics to file
            if opts.verbose:
                print "Writing accuracy metrics to file:",opts.output_accuracy_metrics

            f = open(opts.output_accuracy_metrics_only,'w+')
            f.write("metric\torganism\tvalue\n")
            lines =[]
            for organism in accuracy_metric_results.keys():
                for metric in accuracy_metric_results[organism].keys():
                    lines.append('\t'.join([metric,organism,\
                      str(accuracy_metric_results[organism][metric])])+'\n')
            f.writelines(sorted(lines))
            f.close()
            exit()


    if opts.verbose:
        print "Generating predictions using method:",opts.prediction_method

    if opts.weighting_method == 'exponential':
        #For now, use exponential weighting
        weight_fn = make_neg_exponential_weight_fn(e)

    variances=None #Overwritten by methods that calc variance
    confidence_intervals=None #Overwritten by methods that calc variance

    if opts.prediction_method == 'asr_and_weighting':
        # Perform predictions using reconstructed ancestral states

        if opts.reconstruction_confidence:
            predictions,variances,confidence_intervals =\
              predict_traits_from_ancestors(tree,nodes_to_predict,\
              trait_label=trait_label,\
              lower_bound_trait_label="lower_bound",\
              upper_bound_trait_label="upper_bound",\
              calc_confidence_intervals = True,\
              brownian_motion_parameter=brownian_motion_parameter,\
              weight_fn=weight_fn,verbose=opts.verbose,
              round_predictions=round_opt)

        else:
             predictions =\
              predict_traits_from_ancestors(tree,nodes_to_predict,\
              trait_label=trait_label,\
              weight_fn =weight_fn,verbose=opts.verbose,
              round_predictions=round_opt)

    elif opts.prediction_method == 'weighting_only':
        #Ignore ancestral information
        predictions =\
          weighted_average_tip_prediction(tree,nodes_to_predict,\
          trait_label=trait_label,\
          weight_fn =weight_fn,verbose=opts.verbose)



    elif opts.prediction_method == 'nearest_neighbor':

        predictions = predict_nearest_neighbor(tree,nodes_to_predict,\
          trait_label=trait_label,tips_only = True)

    elif opts.prediction_method == 'random_neighbor':

        predictions = predict_random_neighbor(tree,\
          nodes_to_predict,trait_label=trait_label)

    if opts.verbose:
        print "Done making predictions."

    make_output_dir_for_file(opts.output_trait_table)

    out_fh=open(opts.output_trait_table,'w')
    #Generate the table of biom predictions
    if opts.verbose:
        print "Converting results to .biom format for output..."

    biom_predictions=biom_table_from_predictions(predictions,table_headers,\
                                                         observation_metadata=None,\
                                                         sample_metadata=accuracy_metric_results,convert_to_int=False)
    if opts.verbose:
        print "Writing prediction results to file: ",opts.output_trait_table

    if opts.output_precalc_file_in_biom:

        #write biom table to file
        write_biom_table(biom_predictions, opts.output_trait_table)

    else:
        #convert to precalc (tab-delimited) format

        out_fh = open(opts.output_trait_table, 'w')
        out_fh.write(convert_biom_to_precalc(biom_predictions))
        out_fh.close()

    #Write out variance information to file
    if variances:

        if opts.verbose:
            print "Converting variances to BIOM format"

        if opts.output_precalc_file_in_biom:
            suffix='.biom'
        else:
            suffix='.tab'

        biom_prediction_variances=biom_table_from_predictions({k:v['variance'] for k,v in variances.iteritems()},table_headers,\
        observation_metadata=None,\
        sample_metadata=None,convert_to_int=False)
        outfile_base,extension = splitext(opts.output_trait_table)
        variance_outfile = outfile_base+"_variances"+suffix
        make_output_dir_for_file(variance_outfile)

        if opts.verbose:
            print "Writing variance information to file:",variance_outfile

        if opts.output_precalc_file_in_biom:
            write_biom_table(biom_prediction_variances, variance_outfile)
        else:
            open(variance_outfile,'w').write(\
                convert_biom_to_precalc(biom_prediction_variances))


    if confidence_intervals:

        if opts.verbose:
            print "Converting upper confidence interval values to BIOM format"

        biom_prediction_upper_CI=biom_table_from_predictions({k:v['upper_CI'] for k,v in confidence_intervals.iteritems()},table_headers,\
          observation_metadata=None,\
          sample_metadata=None,convert_to_int=False)

        outfile_base,extension = splitext(opts.output_trait_table)
        upper_CI_outfile = outfile_base+"_upper_CI"+suffix
        make_output_dir_for_file(upper_CI_outfile)

        if opts.verbose:
            print "Writing upper confidence limit information to file:",upper_CI_outfile

        if opts.output_precalc_file_in_biom:
            write_biom_table(biom_prediction_upper_CI, upper_CI_outfile)
        else:
            open(upper_CI_outfile,'w').write(\
                convert_biom_to_precalc(biom_prediction_upper_CI))

        biom_prediction_lower_CI=biom_table_from_predictions({k:v['lower_CI'] for k,v in confidence_intervals.iteritems()},table_headers,\
          observation_metadata=None,\
          sample_metadata=None,convert_to_int=False)

        outfile_base,extension = splitext(opts.output_trait_table)
        lower_CI_outfile = outfile_base+"_lower_CI"+suffix
        make_output_dir_for_file(lower_CI_outfile)

        if opts.verbose:
            print "Writing lower confidence limit information to file",lower_CI_outfile

        if opts.output_precalc_file_in_biom:
            write_biom_table(biom_prediction_lower_CI, lower_CI_outfile)
        else:
            open(lower_CI_outfile,'w').write(\
                convert_biom_to_precalc(biom_prediction_lower_CI))


if __name__ == "__main__":
    main()
