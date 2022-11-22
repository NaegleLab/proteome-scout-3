from app.config import strings
from flask import render_template, redirect, request
# from flask_paginate import Pagination, get_page_parameter
from flask_login import current_user
from app.main.views.proteins import bp
from app.database import protein, modifications

from app.main.forms.search_form import ProteinSearchForm


def perform_query(form):
    search = form.protein.data
    peptide = form.peptide.data
    species = form.species.data
    protein_names = form.protein_names.data

    if search == '':
        search = None

    if peptide == '':
        peptide = None

    if species == 'all' or species == '':
        species = None

    
    
    
    protein_cnt, proteins = protein.search_proteins(
        search=search,
        species=species,
        sequence=peptide,
        page=None,
        exp_id=None,
        includeNames=protein_names)

    return  proteins



def get_protein_metadata(prot, metadata_map, user, exp_id=None):
    

    measured = modifications.get_measured_peptides_by_protein(prot.id, user)

    exp_ids = set()
    residues = set()
    ptms = set()
    sites = set()

    for ms in measured:
        exp_ids.add(ms.experiment_id)

    if exp_id:
        measured = [ms for ms in measured if ms.experiment_id == exp_id]

    for ms in measured:
        for mspep in ms.peptides:
            residues.add(mspep.peptide.site_type)
            sites.add(mspep.peptide.site_pos)
            ptms.add(mspep.modification.name)

    metadata_map[prot.id] = (
        prot,
        len(prot.sequence),
        len(exp_ids),
        len(sites),
        ','.join(residues),
        ', '.join(ptms))


@bp.route('/', methods=['GET', 'POST'])
def search():
    search = False
    # page = request.args.get(get_page_parameter(), type=int, default=1)

    form = ProteinSearchForm()
    user = current_user if current_user.is_authenticated else None

    if form.validate_on_submit():
        # return redirect(url_for('protein_bp.search'))
        
        proteins = perform_query(form)
        protein_metadata = {}
        for p in proteins:
            get_protein_metadata(p, protein_metadata, user)

        # pagination = Pagination(page=page, total=len(protein_metadata), search=search, record_name='proteins')

        return render_template(
            'proteomescout/proteins/search.html',
            title=strings.protein_search_page_title,
            form=form,
            data=protein_metadata,
            # pagination=pagination
            )

    return render_template(
        'proteomescout/proteins/search.html', 
        title=strings.protein_search_page_title, 
        form=form)
