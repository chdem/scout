from scout.parse.variant.headers import (parse_rank_results_header, parse_header_format, 
                                         parse_vep_header)
from cyvcf2 import VCF

def test_parse_header_format():
    description = '"Consequence annotations from Ensembl VEP. Format: Allele'\
                  '|Consequence|IMPACT|SYMBOL|Gene|Feature_type|Feature"'
    format_info = parse_header_format(description.strip('"'))
    assert format_info == 'Allele|Consequence|IMPACT|SYMBOL|Gene|Feature_type|Feature'

def test_parse_header_format_no_format():
    description = '"Consequence annotations from Ensembl VEP."'
    format_info = parse_header_format(description)
    assert format_info == ''

def test_parse_rank_results_header(variant_clinical_file):
    ## GIVEN a vcf object
    vcf_obj = VCF(variant_clinical_file)
    ## WHEN parsing the rank results header
    rank_results_header = parse_rank_results_header(vcf_obj)
    ## THEN assert the header is returned correct
    assert isinstance(rank_results_header, list)
    assert rank_results_header
    assert 'Consequence' in rank_results_header

def test_parse_vep_header(variant_clinical_file):
    ## GIVEN a vcf object
    vcf_obj = VCF(variant_clinical_file)
    ## WHEN parsing the vep header
    vep_header = parse_vep_header(vcf_obj)
    ## THEN assert the header is returned correct
    assert isinstance(vep_header, list)
    assert vep_header
    assert 'Allele' in vep_header
