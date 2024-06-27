
import sys
import datetime
import os
from flask_sqlalchemy import SQLAlchemy
import csv
from proteomescout_worker.helpers import uniprot_mapping
import pandas as pd
import numpy as np
from app.database import protein, modifications, experiment
from multiprocessing import Pool 
from collections import defaultdict

os.chdir('/Users/logan/proteome-scout-3/')

# xAllows for the importing of modules from the proteomescout-3 app within the script
SCRIPT_DIR = '/Users/saqibrizvi/Documents/NaegleLab/ProteomeScout-3/proteomescout-3'
sys.path.append(SCRIPT_DIR)

from scripts.app_setup import create_app
from scripts.progressbar import ProgressBar
#from app.utils.export_proteins import *
from app.database import protein, modifications, experiment
from app.utils.downloadutils import experiment_metadata_to_tsv, zip_package

# directory variable to be imported
OUTPUT_DIR = "scripts/output"

# database instantiated for the script
db = SQLAlchemy()

# application created within which the script can be run
app = create_app()

# database linked to the app
db.init_app(app)


def get_uniprot_sequence(df):
    accessions = df[df['type'] == 'swissprot']['value'].tolist()

    # Submit a single job with all the accessions
    job_id = uniprot_mapping.submit_id_mapping(from_db="UniProtKB_AC-ID", to_db="UniProtKB-Swiss-Prot", ids=accessions)

    if uniprot_mapping.check_id_mapping_results_ready(job_id):
        link = uniprot_mapping.get_id_mapping_results_link(job_id)
        results = uniprot_mapping.get_id_mapping_results_search(link)

        # Create a dictionary to map accessions to results
        accession_to_result = {result['from']: result for result in results['results']}

        # Define a function that takes an accession and returns the requested value, primary accession, and sequence value
        def get_results(accession):
            if accession in accession_to_result:
                result = accession_to_result[accession]
                requested = result['from']
                primary = result['to']['primaryAccession']
                canonical_seq = result['to']['sequence']['value']
                return pd.Series([requested, primary, canonical_seq])
            else:
                return pd.Series([np.nan, np.nan, np.nan])

        # Apply the function to the 'value' column and create new columns in the DataFrame
        #df[['requested', 'primary', 'canonical_seq']] = df['value'].apply(get_results)
        new_columns = df['value'].apply(get_results)
        new_columns.columns = ['requested', 'primary', 'canonical_seq']
        df = pd.concat([df, new_columns], axis=1)
        print(df.columns)


    return df

# mapping peptide records to proteins 
# Going through the peptide data, this function will find the peptide alignments for the protein data and mismatches
# and return a dataframe of successes and failures
# successes will include when there is a successful alignment, even if in wrong position, but misalignment site will be reported
# failures will include when there is no alignment
# this one is looking for the uniprot defined sequence
# 

def find_peptide_alignments(peptide_data, protein_seq_data):
    # Updated DataFrame columns to include new fields
    successes = pd.DataFrame(columns=['protein_id', 'pep_aligned', 'center_pos', 'site_pos', 'mismatch_positions', 'scansite_date', 'site_type', 'protein_domain_id', 'pep_id'])
    failures = pd.DataFrame(columns=['protein_id', 'pep_aligned', 'center_pos', 'site_pos', 'mismatch_positions', 'scansite_date', 'site_type', 'protein_domain_id', 'pep_id'])
    peptide_dict = {}
    #protein_seq_data = un
    for peptide in peptide_data:
        # Updated to include new fields in the dictionary
        if peptide['protein_id'] in peptide_dict:
            peptide_dict[peptide['protein_id']].append((peptide['pep_aligned'].lower(), peptide['site_pos'], peptide['scansite_date'], peptide['site_type'], peptide['protein_domain_id'], peptide['pep_id']))
        else:
            peptide_dict[peptide['protein_id']] = [(peptide['pep_aligned'].lower(), peptide['site_pos'], peptide['scansite_date'], peptide['site_type'], peptide['protein_domain_id'] ,peptide['pep_id'])]

    print(protein_seq_data.head())
    for _, protein_seq in protein_seq_data.iterrows():
        if protein_seq['protein_id'] in peptide_dict:
            pep_aligned_list = []
            pep_id_list = [] 
            center_positions_list = []
            site_positions_list = []
            mismatch_positions_list = []
            scansite_dates_list = []
            site_types_list = []
            protein_domain_ids_list = []
            failed_mappings_list = []
            for pep_aligned, site_pos, scansite_date, site_type, protein_domain_id, pep_id in peptide_dict[protein_seq['protein_id']]:
                if isinstance(protein_seq['canonical_seq'], str):
                    index = protein_seq['canonical_seq'].lower().find(pep_aligned)
                    if index != -1:
                        index += 1  # Adjust for 1-indexing
                        center_index = index + len(pep_aligned) // 2
                        pep_aligned_list.append(pep_aligned)
                        center_positions_list.append(str(center_index))
                        site_positions_list.append(str(site_pos))
                        scansite_dates_list.append(scansite_date)
                        site_types_list.append(site_type)
                        protein_domain_ids_list.append(protein_domain_id)
                        pep_id_list.append(pep_id)
                        if center_index != site_pos:
                            mismatch_positions_list.append((str(center_index), str(site_pos)))
                            failed_mappings_list.append((pep_aligned, site_pos, scansite_date, site_type, protein_domain_id, pep_id))
                else:
                    failed_mappings_list.append((pep_aligned, site_pos, scansite_date, site_type, protein_domain_id, pep_id))
            if pep_aligned_list and not mismatch_positions_list:  # Check for successful mappings without mismatches
                successes.loc[len(successes)] = [
                    protein_seq['protein_id'], 
                    ';'.join(map(str, pep_aligned_list)), 
                    ';'.join(map(str, center_positions_list)), 
                    ';'.join(map(str, site_positions_list)), 
                    ';'.join([f"{str(center)}:{str(site)}" for center, site in mismatch_positions_list]), 
                    ';'.join(map(str, scansite_dates_list)), 
                    ';'.join(map(str, site_types_list)), 
                    ';'.join(map(str, protein_domain_ids_list)),
                    ';'.join(map(str, pep_id_list))
                ]
            if failed_mappings_list:
                #failures.loc[len(failures)] = [protein_seq['protein_id'], ';'.join([pep[0] for pep in failed_mappings_list]), ';'.join(center_positions_list), ';'.join([str(pep[1]) for pep in failed_mappings_list]), ';'.join(site_positions_list), ';'.join([pep[2] for pep in failed_mappings_list]), ';'.join([pep[3] for pep in failed_mappings_list]), ';'.join([pep[4] for pep in failed_mappings_list])]
                failures.loc[len(failures)] = [
                    protein_seq['protein_id'], 
                    ';'.join(map(str, pep_aligned_list)), 
                    ';'.join(map(str, center_positions_list)), 
                    ';'.join(map(str, site_positions_list)), 
                    ';'.join([f"{str(center)}:{str(site)}" for center, site in mismatch_positions_list]), 
                    ';'.join(map(str, scansite_dates_list)), 
                    ';'.join(map(str, site_types_list)), 
                    ';'.join(map(str, protein_domain_ids_list)),
                    ';'.join(map(str, pep_id_list))
                ]
            print('FAILURES', failures)
    return successes, failures


def adjust_peptide(peptide):
    # Step 1: Ensure the peptide is capitalized
    peptide = peptide.upper()
    # Step 2: Find the central residue index
    center_index = len(peptide) // 2
    # Step 3: Make the central residue lowercase
    if len(peptide) % 2 == 1:  # Ensure the peptide has an odd length
        peptide = peptide[:center_index] + peptide[center_index].lower() + peptide[center_index + 1:]
    else:
        # Handle even length peptides if necessary
        # This example simply lowers the character right at the center
        # Adjust as needed based on your requirements
        peptide = peptide[:center_index-1] + peptide[center_index-1].lower() + peptide[center_index:].upper()
    return peptide



def process_peptide_mismatches(failures_df):
    expanded_failures = []
    for index, row in failures_df.iterrows():
        protein_id = row['protein_id']

        pep_id_list = row['pep_id'].split(';')
        pep_aligned_list = row['pep_aligned'].split(';')
        center_positions_list = row['center_pos'].split(';')
        site_type_list = row['site_type'].split(';')

        for pep_id, pep_aligned, center_pos, site_type in zip(pep_id_list, pep_aligned_list, center_positions_list, site_type_list):
            # Ensure center_pos is zero-based; adjust if necessary
            center_index = int(center_pos) - 1  # Adjust if center_pos is one-based
            # Capitalize the peptide string and make the center residue lowercase
            pep_aligned_processed = pep_aligned.upper()
            if 0 <= center_index < len(pep_aligned):
                pep_aligned_processed = (
                    pep_aligned_processed[:center_index] +
                    pep_aligned_processed[center_index].lower() +
                    pep_aligned_processed[center_index + 1:]
                )

            expanded_failures.append({
                'protein_id': protein_id,
                'pep_id': pep_id,
                'site_pos': center_pos,
                'pep_aligned': pep_aligned_processed, 
                'site_type': site_type,
            })

        result = pd.DataFrame(expanded_failures)
        result['pep_aligned'] = result['pep_aligned'].apply(adjust_peptide)
    
    return result


def process_peptide_matches(success_df):
    expanded_successes = []
    for index, row in success_df.iterrows():
        protein_id = row['protein_id']

        pep_id_list = row['pep_id'].split(';')
        pep_aligned_list = row['pep_aligned'].split(';')
        site_pos_list = row['site_pos'].split(';')
        site_type_list = row['site_type'].split(';')

        for pep_id, pep_aligned, site_pos, site_type in zip(pep_id_list, pep_aligned_list, site_pos_list, site_type_list):
            # Ensure site_pos is zero-based; adjust if necessary
            center_index = int(site_pos) - 1  # Adjust if site_pos is one-based
            # Capitalize the peptide string and make the center residue lowercase
            pep_aligned_processed = pep_aligned.upper()
            if 0 <= center_index < len(pep_aligned):
                pep_aligned_processed = (
                    pep_aligned_processed[:center_index] +
                    pep_aligned_processed[center_index].lower() +
                    pep_aligned_processed[center_index + 1:]
                )

            expanded_successes.append({
                'protein_id': protein_id,
                'pep_id': pep_id,
                'site_pos': site_pos,
                'pep_aligned': pep_aligned_processed, 
                'site_type': site_type,
            })
        result = pd.DataFrame(expanded_successes)
        result['pep_aligned'] = result['pep_aligned'].apply(adjust_peptide)
    
    return result

# to process dataframes of successful sequence mapping to uniprot. Should just add a current tag to protein_id
# Need to continue fixing this ONE 
def update_protein_status_df(df):
    df = df.dropna()
    protein_ids = df['protein_id'].tolist() 
    protein_records = protein.Protein.query.filter(protein.Protein.id.in_(protein_ids)).all()

    for protein in protein_records: 
        protein.current = 1
    
    db.session.flush() 

    # Inspect changes (this is just an example, adjust according to your model)
    updated_proteins = protein.Protein.query.filter(protein.Protein.id.in_(protein_ids)).all()
    for protein in updated_proteins:
        print(f"Protein ID: {protein.id}, Current: {protein.current}")
    
    db.session.rollback()



# Processing of proteins with uniprot sequences that do not match the database sequence.
# Function will find these, retain old protein_id to query other items, and commit with new records 
# Needs to be fed failures_df from find_peptide_alignments
def process_sequence_changes_and_commit(df, commit=True):
    df = df.dropna()
    old_protein_ids = df['protein_id'].tolist()
    new_protein_records = []
    df['current'] = 1 # setting the current status of the protein to 1

    for index, row in df.iterrows():
        # Step 1: Instantiate the Protein object without arguments
        new_protein = protein.Protein()
        # Step 2: Set attributes individually
        new_protein.sequence = row['canonical_seq']
        new_protein.species_id = row['species_id']
        new_protein.acc_gene = row['acc_gene']
        new_protein.locus = row['locus']
        new_protein.name = row['name']
        new_protein.current = row['current']
        new_protein.date = datetime.datetime.now().date()
     

        # Step 3: Add the new Protein to the session
        db.session.add(new_protein)
        new_protein_records.append(new_protein)

    # Flush the session to get the new IDs assigned
    db.session.flush()

    updated_data = [
        {
            'new_protein_id': protein.id,  # Fetch the new ID assigned by the database
            'name': protein.name,
            'canonical_seq': protein.sequence,
            'species_id': protein.species_id,
            'acc_gene': protein.acc_gene,
            'locus': protein.locus, 
            'current': protein.current
        }
        for protein in new_protein_records
    ]

    updated_df = pd.DataFrame(updated_data)
    updated_df['old_protein_id'] = old_protein_ids
    print(updated_df)

    if commit:
        db.session.commit()
        print("Changes committed.")
    else:
        db.session.rollback()
        print("Changes rolled back.")

    # Return the updated DataFrame
    return updated_df

# Function to replicate peptide records for protein_ids following sequence changes and addition of new records to db 
# Will add new entries partially replicated from old entries, but with new protein_ids, and potentially new mapping 
# Requires the dataframe produced from process_sequence_changes_and_commit
def process_and_commit_new_peptides(df, new_prot_df, commit = True): 
    old_peptide_ids = df['pep_id'].tolist()
    old_protein_ids = df['protein_id'].tolist()
    #new_protein_ids = new_prot_df['new_protein_id'].tolist()

    new_peptide_records = [] 

    protein_id_mapping = dict(zip(new_prot_df['old_protein_id'], new_prot_df['new_protein_id']))

    df['new_protein_id'] = df['protein_id'].map(protein_id_mapping)
    new_peptide_records = [] 

    for index, row in df.iterrows():
        # Step 1: Instantiate the Protein object without arguments
        new_peptide = modifications.Peptide()

        # Step 2: Set attributes individually
        new_peptide.pep_aligned = row['pep_aligned']
        new_peptide.site_pos = row['site_pos']
        new_peptide.site_type = row['site_type']
        new_peptide.protein_id = row['new_protein_id']
  
        db.session.add(new_peptide)
        new_peptide_records.append(new_peptide)

    db.session.flush()
    
    updated_pep_data = [
        {
            'new_pep_id': peptide.id,  # Fetch the new ID assigned by the database
            'pep_aligned': peptide.pep_aligned,
            'site_pos': peptide.site_pos,
            'site_type': peptide.site_type,
            'protein_id': peptide.protein_id
        }
        for peptide in new_peptide_records
    ]

    updated_peptides = pd.DataFrame(updated_pep_data)
    updated_peptides['old_protein_id'] = old_protein_ids
    updated_peptides['old_pep_id'] = old_peptide_ids
    print(updated_peptides)

    if commit:
        db.session.commit()
        print("Changes committed.")
    else:
        db.session.rollback()
        print("Changes rolled back.")

    # Return the updated DataFrame
    return updated_peptides

### Function to be called after creating new peptide entries for proteins with changed sequences/updated entries
### Requires the result of process_and_commit_new_peptides and the dataframe of peptide modifications sourced from querying the database for mods 
### with peptide_ids = old_peptide ids
### Will create new partial duplicate entries for the peptide modifications with new peptide_ids that associate to new protein entries 
def create_new_MS_mods_for_peptides(df_mods, new_pep_df, commit=True): 
    
    print(f"Initial df_mods entries: {len(df_mods)}")
    
    old_peptide_ids = df_mods['pep_id'].tolist()
    
    pep_id_to_new_pep_id = new_pep_df.set_index('old_pep_id')['new_pep_id'].to_dict()
    
    df_mods['pep_id'] = df_mods['pep_id'].astype(str)
    
    # Map old_pep_id to new_pep_id
    df_mods['new_pep_id'] = df_mods['pep_id'].map(pep_id_to_new_pep_id)
    
    # Optional: Handle rows with NaN in 'new_pep_id' if necessary
    # df_mods = df_mods.dropna(subset=['new_pep_id'])
    
    print(f"Entries after mapping: {len(df_mods)}")
    
    new_mod_records = []
    

    for index, row in df_mods.iterrows():
        # Step 1: Instantiate the Protein object without arguments
        new_mod = modifications.PeptideModification()

        # Step 2: Set attributes individually
        new_mod.MS_id = row['MS_id']
        new_mod.modification_id = row['modificiation_id']
        new_mod.peptide_id = row['new_pep_id']
  
        db.session.add(new_mod)
        new_mod_records.append(new_mod)

    db.session.flush()

    updated_mod_data = [
        {
            'new_mod_id': mod.id,  # Fetch the new ID assigned by the database
            'MS_id': mod.MS_id,
            'modification_id': mod.modification_id,
            'pep_id': mod.peptide_id
        }
        for mod in new_mod_records
    ]

    updated_mods = pd.DataFrame(updated_mod_data)
    updated_mods['old_pep_ids'] = old_peptide_ids
    
    print(updated_mods)

    if commit:
        db.session.commit()
        print("Changes committed.")
    else:
        db.session.rollback()
        print("Changes rolled back.")

    # Return the updated DataFrame
    return updated_mods

    



with app.app_context():
    # Fetch all protein entries
    protein_seq = protein.Protein.query.limit(100).all()

    # Step 1: Collect all accessions
    accession_to_protein = defaultdict(list)
    #print(accession_to_protein.keys())


    for entry in protein_seq:
        protein_acc = protein.ProteinAccession.query.filter_by(protein_id=entry.id, type='swissprot').all()
        for accession in protein_acc:
            accession_to_protein[accession.value].append({
            'protein_id': entry.id,
            'name': entry.name,
            'sequence': entry.sequence,
            'species_id': entry.species_id,
            'locus': entry.locus,
            'acc_gene': entry.acc_gene,
            'name': entry.name,
                # Assuming you want to keep the sequence for comparison
        })
    
    #print(entry)
    
    # Prepare DataFrame for batch request
    #df = pd.DataFrame({'type': ['swissprot'] * len(accession_to_protein), 'value': list(accession_to_protein.keys())})
    df = pd.DataFrame({
        'type': ['swissprot'] * len(accession_to_protein),
        'value': list(accession_to_protein.keys()),
        'protein_id': [entry['protein_id'] for value_list in accession_to_protein.values() for entry in value_list]
        })
    #print(df)
    
    # Step 2: Batch request to UniProt
    df = get_uniprot_sequence(df)
    df = df.drop(['type', 'requested', 'value'], axis=1)
    df = df.drop_duplicates(subset=['protein_id']) # removing duplicate protein_ids before processing
    
    # collecting instances of protein sequences that match the current uniprot sequence or dont match
    unmatched_entries = []
    
    matched_entries = [] 
    # Step 3: Process sequences
    for index, row in df.iterrows():
        uniprot_sequence = row['canonical_seq']
        accession_value = row['primary']
        protein_id = row['protein_id']
        print(f"Processing Accession: {accession_value}, UniProt Sequence: {uniprot_sequence}")
     
        # Get the protein entries associated with this accession
        entries = accession_to_protein[accession_value]

        for entry in entries:
            print(f"  Checking Protein ID: {entry['protein_id']}")
            if uniprot_sequence != entry['sequence']:
                entry['canonical_seq'] = uniprot_sequence  # Add the uniprot_sequence to the entry
                unmatched_entries.append(entry)
            else: 
                print(f"    Sequence Match: Marking protein ID {entry['protein_id']} as current.")
                matched_entries.append(entry)
                
    #print(unmatched_entries)
    unmatched_df = pd.DataFrame(unmatched_entries)
    matched_df = pd.DataFrame(matched_entries) # need to set status of these as current in the database

    # updating the matched entries in db as current 
    #update_protein_status_df(matched_df)
    # commit unmatched_df protein entries to the database

    unmatched_protein_ids = [entry['protein_id'] for entry in unmatched_entries]

    # adding new protein entries for new protein sequences to the database and retaining old info for association
    updated_seq_df = process_sequence_changes_and_commit(unmatched_df, commit=False)


    # Now, query for all peptides that have a protein_id in unmatched_protein_ids
    unmatched_peptides = modifications.Peptide.query.filter(modifications.Peptide.protein_id.in_(unmatched_protein_ids)).all()

                # converting the peptides data into a dataframe 
    peptide_data = []
    for p in unmatched_peptides:
        peptide_data.append({
            'pep_id': p.id,
            'scansite_date': p.scansite_date,
            'pep_aligned': p.pep_aligned, 
            'site_pos': p.site_pos, 
            'site_type': p.site_type,
            'protein_domain_id': p.protein_domain_id,
            'protein_id': p.protein_id,
            })

    peptide_df = pd.DataFrame(peptide_data)
                #print(df)
                # Call find_peptide_alignments
    successes, failures = find_peptide_alignments(peptide_data, unmatched_df)

    successes = process_peptide_matches(successes)
    failures = process_peptide_mismatches(failures)

    all_peptides = pd.concat([successes, failures], axis=0)

    # Getting teh 
    # Assuming 'successes' is your DataFrame and it contains a column 'pep_id' with the peptide IDs
    old_pep_ids = all_peptides['pep_id'].to_list()

    # Add line to commit new peptides and retrieve the new IDs associated with them 
    # Now, use these pep_ids to filter PeptideModification entries
    mods_data = modifications.PeptideModification.query.filter(modifications.PeptideModification.peptide_id.in_(old_pep_ids)).all()

    mods = []
    for m in mods_data:
        mods.append({
            'mod_id': m.id,
            'MS_id': m.MS_id,
            'pep_id': m.peptide_id, 
            'modificiation_id': m.modification_id,
            })
    mods_df = pd.DataFrame(mods)
    

    