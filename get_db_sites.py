import sys
import pickle
import itertools
from collections import Counter, defaultdict
from indra.databases import uniprot_client
from indra.tools import assemble_corpus as ac
from indra.util import read_unicode_csv, write_unicode_csv
from protmapper import ProtMapper


def get_db_phos_stmts(filename):
    from indra_db.client import get_statements_by_gene_role_type
    phos_stmts = get_statements_by_gene_role_type(
                        stmt_type='Phosphorylation', fix_refs=False,
                        preassembled=False,
                        with_evidence=True, with_support=False)
    with open(filename, 'wb') as f:
        pickle.dump(phos_stmts, f)
    return phos_stmts


def preprocess_db_stmts(stmts, output_file):
    """Take the statements from the database and grounding map them; """
    print("Mapping grounding")
    gmap_stmts = ac.map_grounding(stmts)
    #ac.dump_statements(gmap_stmts, prefix + '_gmap.pkl')
    print("Sorting and filtering")
    # Next, eliminate exact duplicates
    stmts_by_deep_hash = [(s.get_hash(shallow=False), s) for s in gmap_stmts]
    stmts_by_deep_hash.sort(key=lambda x: x[0])
    uniq_stmts = []
    for k, group in itertools.groupby(stmts_by_deep_hash, key=lambda x: x[0]):
        uniq_stmts.append(list(group)[0][1])
    # Filter to statements with residue and position
    site_stmts = [s for s in uniq_stmts if s.residue and s.position]
    ac.dump_statements(site_stmts, output_file)
    return site_stmts


def get_stmts_by_site(phos_stmts, filename=None):
    # First filter statements to those that have objects with uniprot IDs
    filt_stmts = [s for s in phos_stmts if s.sub.db_refs.get('UP')]
    gene_sites = []
    stmts_by_site = {}
    for s in filt_stmts:
        if s.enz is None:
            continue
        site = (s.sub.db_refs.get('UP'), s.residue, s.position)
        if site in stmts_by_site:
            stmts_by_site[site].append(s)
        else:
            stmts_by_site[site] = [s]
    if filename:
        with open(filename, 'wb') as f:
            pickle.dump(stmts_by_site, f)
    return stmts_by_site


def site_cache_stats():
    sm = SiteMapper(use_cache=True)
    ms_desc_list = []
    examples = defaultdict(list)
    for site_key, mapped_site in sm._cache.items():
        if mapped_site is not None:
            ms_desc_list.append(mapped_site.description)
            if mapped_site.description in (
                           'INFERRED_ALTERNATIVE_ISOFORM',
                           'INFERRED_MOUSE_SITE',
                           'INFERRED_RAT_SITE',
                           'INFERRED_METHIONINE_CLEAVAGE',
                           'NO_MAPPING_FOUND'):
                examples[mapped_site.description].append(mapped_site)
        else:
            ms_desc_list.append('NO_MAPPING_FOUND')

    ctr = Counter(ms_desc_list)
    ctr = sorted([(k, v) for k, v in ctr.items()],
                 key=lambda x: x[1], reverse=True)
    return ctr, examples


if __name__ == '__main__':
    # Get statements from INDRA database
    if sys.argv[1] == 'get_phos_stmts':
        get_db_phos_stmts(sys.argv[2])
    # Map grounding, remove identical statements
    elif sys.argv[1] == 'preprocess_stmts':
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        input_stmts = ac.load_statements(input_file)
        preproc_stmts = preprocess_db_stmts(input_stmts, output_file)
    elif sys.argv[1] == 'stmts_by_site':
        input_file = sys.argv[2]
        output_file = sys.argv[3]
        input_stmts = ac.load_statements(input_file)
        get_stmts_by_site(input_stmts, output_file)
    else:
        print("Argument must be get_phos_stmts or map_grounding.")
        print(sys.argv)
        sys.exit(1)

    """
    preproc_stmts = \
            ac.load_statements('output/db_phos_stmts_gmap_uniq_pos_enz.pkl')
    stmts_by_site = get_stmts_by_site(preproc_stmts, 'output/stmts_by_site.pkl')

    #gene_sites = get_db_sites(reload=True, phos_stmts=phos_stmts)
    gene_sites = get_db_sites(reload=False)
    import random
    random.seed(1)
    random.shuffle(gene_sites)
    gene_sites = gene_sites[0:1000]
    sm = SiteMapper(use_cache=True)
    site_list = [(gs[0], 'uniprot', gs[3], gs[4]) for gs in gene_sites]
    mapped_sites = sm.map_sitelist_to_human_ref(site_list)
    with open('sm_cache.pkl', 'wb') as f:
        import pickle
        pickle.dump(sm._cache, f)
    site_ctr, examples = site_cache_stats()
    """

