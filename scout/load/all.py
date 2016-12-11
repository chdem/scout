# -*- coding: utf-8 -*-
import logging

from . import load_case, load_variants, delete_variants
from scout.parse.case import parse_case
from scout.build import build_case

log = logging.getLogger(__name__)

def load_scout(adapter, config, ped=None, update=False):
    """Load a new case from a Scout config."""
    log.debug('parse case data from config and ped')
    case_data = parse_case(config, ped)
    log.debug('build case object from parsed case data')
    case_obj = build_case(case_data)
    log.debug('load case object into database')
    load_case(adapter, case_obj, update=update)

    log.info("Delete variants for case %s", case_obj.case_id)
    delete_variants(adapter=adapter, case_obj=case_obj)

    hgnc_genes = {}
    # for gene in adapter.all_genes():
    #     hgnc_genes[gene.hgnc_id] = gene

    log.info("Load SNV variants for case %s", case_obj.case_id)
    load_variants(adapter=adapter, variant_file=config['vcf_snv'],
                  case_obj=case_obj, variant_type='clinical', category='snv',
                  hgnc_genes=hgnc_genes,
                  rank_treshold=config.get('rank_threshold'))

    if config.get('vcf_sv'):
        log.info("Load SV variants for case %s", case_obj.case_id)
        load_variants(adapter=adapter, variant_file=config['vcf_sv'],
                      case_obj=case_obj, variant_type='clinical',
                      category='sv', hgnc_genes=hgnc_genes,
                      rank_treshold=config.get('rank_threshold'))

        case_obj.has_svvariants = True
        case_obj.save()
