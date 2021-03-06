import logging

logger = logging.getLogger(__name__)

from scout.constants import (SPIDEX_HUMAN)

class QueryHandler(object):

    def build_query(self, case_id, query=None, variant_ids=None, category='snv'):
        """Build a mongo query

        These are the different query options:
            {
                'genetic_models': list,
                'thousand_genomes_frequency': float,
                'exac_frequency': float,
                'clingen_ngi': int,
                'cadd_score': float,
                'cadd_inclusive": boolean,
                'genetic_models': list(str),
                'hgnc_symbols': list,
                'region_annotations': list,
                'functional_annotations': list,
                'clinsig': list,
                'clinsig_confident_always_returned': boolean,
                'variant_type': str(('research', 'clinical')),
                'chrom': str,
                'start': int,
                'end': int,
                'svtype': list,
                'gene_panels': list(str),
            }

        Arguments:
            case_id(str)
            query(dict): A dictionary with querys for the database
            variant_ids(list(str)): A list of md5 variant ids

        Returns:
            mongo_query : A dictionary in the mongo query format

        """
        query = query or {}
        mongo_query = {}
        logger.debug("Building a mongo query for %s" % case_id)
        mongo_query['case_id'] = case_id
        logger.debug("Querying category %s" % category)
        mongo_query['category'] = category

        # We need to check if there is any query specified in the input query
        mongo_query['variant_type'] = query.get('variant_type', 'clinical')
        logger.debug("Set variant type to %s", mongo_query['variant_type'])

        # Requests to filter based on gene panels, hgnc_symbols or
        # coordinate ranges must always be honored. They are always added to
        # query as top level, implicit '$and'.

        if query.get('hgnc_symbols') and query.get('gene_panels'):
            gene_query = [
                        {'hgnc_symbols': {'$in': query['hgnc_symbols']}},
                        {'panels': {'$in': query['gene_panels']}}
                    ]
            mongo_query['$or']=gene_query
        else:
            if query.get('hgnc_symbols'):
                hgnc_symbols = query['hgnc_symbols']
                mongo_query['hgnc_symbols'] = {'$in': hgnc_symbols}
                logger.debug("Adding hgnc_symbols: %s to query" %
                             ', '.join(hgnc_symbols))

            if query.get('gene_panels'):
                gene_panels = query['gene_panels']
                mongo_query['panels'] = {'$in': gene_panels}

        if query.get('chrom'):
            chromosome = query['chrom']
            mongo_query['chromosome'] = chromosome
            #Only check coordinates if there is a chromosome
            if (query.get('start') and query.get('end')):
                mongo_query['position'] = {
                                                '$lte': int(query['end'])
                                        }

                mongo_query['end'] = {
                                        '$gte': int(query['start'])
                                    }

        mongo_query_minor = []

        # A minor, excluding filter criteria will hide variants in general,
        # but can be overridden by an including, major filter criteria
        # such as a Pathogenic ClinSig.
        # If there are no major criteria given, all minor criteria are added as a
        # top level '$and' to the query.
        # If there is only one major criteria given without any minor, it will also be
        # added as a top level '$and'.
        # Otherwise, major criteria are added as a high level '$or' and all minor criteria
        # are joined together with them as a single lower level '$and'.

        mongo_query_minor = []

        if query.get('thousand_genomes_frequency') is not None:
            thousandg = query.get('thousand_genomes_frequency')
            if thousandg == '-1':
                mongo_query['thousand_genomes_frequency'] = {
                                                                '$exists': False
                                                            }

            else:
                # Replace comma with dot
                mongo_query_minor.append(
                    {
                        '$or': [
                            {
                                'thousand_genomes_frequency':
                                    {
                                        '$lt': float(thousandg)
                                    }
                                },
                            {
                                'thousand_genomes_frequency':
                                    {
                                        '$exists': False
                                    }
                            }
                        ]
                    }
                )
            logger.debug("Adding thousand_genomes_frequency to query")

        if query.get('exac_frequency') is not None:
            exac = query['exac_frequency']
            if exac == '-1':
                mongo_query['exac_frequency'] = {'$exists': False}
            else:
                mongo_query_minor.append({
                    '$or': [
                        {'exac_frequency': {'$lt': float(exac)}},
                        {'exac_frequency': {'$exists': False}}
                    ]
                })

        if query.get('local_obs') is not None:
            mongo_query_minor.append({
                '$or': [
                    {'local_obs_old': None},
                    {'local_obs_old': {'$lt': query['local_obs'] + 1}},
                ]
            })

        if query.get('clingen_ngi') is not None:
            mongo_query_minor.append({
                '$or': [
                    {'clingen_ngi': {'$exists': False}},
                    {'clingen_ngi': {'$lt': query['clingen_ngi'] + 1}},
                ]
            })

        if query.get('spidex_human'):
            # construct spidex query. Build the or part starting with empty SPIDEX values
            spidex_human = query['spidex_human']

            spidex_query_or_part = []
            if ( 'not_reported' in spidex_human):
                spidex_query_or_part.append({'spidex': {'$exists': False}})

            for spidex_level in SPIDEX_HUMAN:
                if ( spidex_level in spidex_human ):
                    spidex_query_or_part.append({'$or': [ 
                                {'$and': [{'spidex': {'$gt': SPIDEX_HUMAN[spidex_level]['neg'][0]}},
                                          {'spidex': {'$lt': SPIDEX_HUMAN[spidex_level]['neg'][1]}}]},
                                {'$and': [{'spidex': {'$gt': SPIDEX_HUMAN[spidex_level]['pos'][0]}},
                                          {'spidex': {'$lt': SPIDEX_HUMAN[spidex_level]['pos'][1]}} ]} ]})
            
            mongo_query_minor.append({'$or': spidex_query_or_part })

        if query.get('cadd_score') is not None:
            cadd = query['cadd_score']
            cadd_query = {'cadd_score': {'$gt': float(cadd)}}
            logger.debug("Adding cadd_score: %s to query", cadd)

            if query.get('cadd_inclusive') is True:
                cadd_query = {
                    '$or': [
                        cadd_query,
                        {'cadd_score': {'$exists': False}}
                        ]}
                logger.debug("Adding cadd inclusive to query")

            mongo_query_minor.append(cadd_query)

        if query.get('genetic_models'):
            models = query['genetic_models']
            mongo_query_minor.append({'genetic_models': {'$in': models}})

            logger.debug("Adding genetic_models: %s to query" %
                         ', '.join(models))

        if query.get('functional_annotations'):
            functional = query['functional_annotations']
            mongo_query_minor.append({'genes.functional_annotation': {'$in': functional}})

            logger.debug("Adding functional_annotations %s to query" %
                         ', '.join(functional))

        if query.get('region_annotations'):
            region = query['region_annotations']
            mongo_query_minor.append({'genes.region_annotation': {'$in': region}})

            logger.debug("Adding region_annotations %s to query" %
                         ', '.join(region))

        if query.get('size'):
            size = query['size']
            size_query = {'length': {'$gt': int(size)}}
            logger.debug("Adding length: %s to query" % size)

            if query.get('size_inclusive') == 'yes':
                size_query = {
                    '$or': [
                        size_query,
                        {'length': {'$exists': False}}

                    ]}
                logger.debug("Adding size inclusive to query.")

            mongo_query_minor.append(size_query)

        if query.get('svtype'):
            svtype = query['svtype']
            mongo_query_minor.append({'sub_category': {'$in': svtype}})
            logger.debug("Adding SV_type %s to query" %
                         ', '.join(svtype))

        if query.get('depth'):
            logger.debug("add depth filter")
            mongo_query_minor.append({
                'tumor.read_depth': {
                    '$gt': query.get('depth'),
                }
            })

        if query.get('alt_count'):
            logger.debug("add min alt count filter")
            mongo_query_minor.append({
                'tumor.alt_depth': {
                    '$gt': query.get('alt_count'),
                }
            })

        if query.get('control_frequency'):
            logger.debug("add minimum control frequency filter")
            mongo_query_minor.append({
                'normal.alt_freq': {
                    '$lt': float(query.get('control_frequency')),
                }
            })

        mongo_query_major = None

        # Given a request to always return confident clinical variants,
        # add the clnsig query as a major criteria, but only
        # trust clnsig entries with trusted revstat levels.

        if query.get('clinsig'):
            rank = [int(item) for item in query['clinsig']]

            if query.get('clinsig_confident_always_returned') == True:

                trusted_revision_level = ['mult', 'single', 'exp', 'guideline']

                mongo_query_major = { "clnsig":
                        {
                            '$elemMatch': { 'value':
                                            { '$in': rank },
                                            'revstat':
                                            { '$in': trusted_revision_level }
                                          }
                         }
                    }

            else:
                logger.debug("add CLINSIG filter for rank: %s" %
                             ', '.join(str(query['clinsig'])))
                if mongo_query_minor:
                    mongo_query_minor.append({'clnsig.value': {'$in': rank}})
                else:
                    # if this is the only minor critera, use implicit and.
                    mongo_query['clnsig.value'] = {'$in': rank}

        if mongo_query_minor and mongo_query_major:
            mongo_query['$or'] = [ {'$and': mongo_query_minor }, mongo_query_major ]
        elif mongo_query_minor:
            mongo_query['$and'] = mongo_query_minor
        elif mongo_query_major:
            mongo_query['clnsig'] = mongo_query_major['clnsig']

        if variant_ids:
            mongo_query['variant_id'] = {'$in': variant_ids}

            logger.debug("Adding variant_ids %s to query" % ', '.join(variant_ids))


        logger.debug("mongo query: %s", mongo_query)

        return mongo_query
