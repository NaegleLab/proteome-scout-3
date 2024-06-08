

import sys
import time
import os
from flask_sqlalchemy import SQLAlchemy
import csv
from proteomescout_worker.helpers import uniprot_mapping
import pandas as pd
import numpy as np
import datetime
import logging
from app import celery
from celery import chain
import requests

# Allows for the importing of modules from the proteomescout-3 app within the script
SCRIPT_DIR = '/Users/saqibrizvi/Documents/NaegleLab/ProteomeScout-3/proteomescout-3'
sys.path.append(SCRIPT_DIR)

from scripts.app_setup import create_app
from scripts.progressbar import ProgressBar
from app.utils.export_proteins import *
from app.database import protein, modifications, experiment



# directory variable to be imported
OUTPUT_DIR = "scripts/output"

# database instantiated for the script
db = SQLAlchemy()

# application created within which the script can be run
app = create_app()

# database linked to the app
db.init_app(app)


# Fetching protein accessions and protein sequences from the database
with app.app_context():
    protein_acc = protein.ProteinAccession.query.all()
    protein_seq = protein.Protein.query.all()  # Replace 'OtherTableModel' with the model for the other table

    # Create a list of dictionaries for the protein accession data
    protein_data = []
    for p in protein_acc:
        protein_data.append({
            'id': p.id,
            'type': p.type,
            'value': p.value, 
            'protein_id': p.protein_id, 
            'primary_acc': p.primary_acc
        })

    # Create a list of dictionaries for the other table data
    protein_seq_data = []
    for o in protein_seq:
        protein_seq_data.append({
            'id': o.id,  # Replace 'column1', 'column2', etc. with the actual column names
            'sequence': o.sequence,
            'species_id': o.species_id, 
            'acc_gene': o.acc_gene, 
            'locus': o.locus,
            'name': o.name,
            'date': o.date,
            # Add more columns as needed
        })

    # Convert the lists of dictionaries into DataFrames
    protein_acc_df = pd.DataFrame(protein_data)
    protein_seq_df = pd.DataFrame(protein_seq_data)



# combining the acc_df and seq_df on the protein_id column
def combine_process_protein(acc_df, seq_df): 
    # filter out only primary accessions 
    acc_df = acc_df[acc_df['type'] == 'swissprot']
    acc_df = acc_df[acc_df['primary_acc'] == True]

    # merge the two dataframes 
    combined_df = pd.merge(acc_df, seq_df, left_on='protein_id', right_on='id', how='inner')

    return combined_df


combined_df = combine_process_protein(protein_acc_df, protein_seq_df)


# Using uniprot to fetch protein records for each accession
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
        df[['requested', 'primary', 'canonical_seq']] = df['value'].apply(get_results)
    return(df)

# fetching the uniprot sequence for each protein
combined_df_wseq = get_uniprot_sequence(combined_df)

# seeing if the uniprot sequence matches the sequence in the database
combined_df_wseq['seq_match'] = combined_df_wseq['sequence'] == combined_df_wseq['canonical_seq']


# proteins where sequences match, and don't require an update but need updated date 
equivalent_sequences = combined_df_wseq[combined_df_wseq['seq_match'] == True]

# filtering out the non-equivalent sequences
non_equivalent_sequences = combined_df_wseq[combined_df_wseq['seq_match'] == False]


# Checking if nonequivalent sequences are matched to other isoforms ie when the canonical seq might have changed 

#mismatch_subset = mismatches

def get_isoform_data(accession):
    print(f"Processing {accession}")
    requestURL = f"https://www.ebi.ac.uk/proteins/api/proteins/{accession}/isoforms"
    
    with requests.Session() as session:
        session.headers.update({ "Accept" : "application/json"})
        r = session.get(requestURL)

        if not r.ok:
            if r.status_code == 404:
                print(f"No data for {accession}")
                return pd.Series()  # return an empty Series for 404 errors
            else:
                print(f"processing {accession}")
                r.raise_for_status()
                sys.exit()

        data = r.json()
        row = {}

        for i, isoform in enumerate(data, 1):
            #print(f"Processing isoform {i} for {accession}")
            if 'protein' in isoform and 'recommendedName' in isoform['protein'] and 'fullName' in isoform['protein']['recommendedName']:
                row[f"Isoform {i} Accession"] = isoform['accession']
            if 'sequence' in isoform:
                row[f"Isoform {i} Sequence"] = isoform['sequence']['sequence']

        return pd.Series(row)
# run in batches to avoid overwhelming the server
df = pd.DataFrame()

for i in range(0, len(mismatched), 500):
    batch = mismatched[i:i+500]
    batch_isoforms = batch.join(batch['value'].apply(get_isoform_data))
    df = df.append(batch_isoforms, ignore_index=True)
    time.sleep(60)  # wait for 1 minute

mismatches_isoforms = df