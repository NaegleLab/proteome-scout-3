from flask import render_template
from flask_login import current_user
from app.database import experiment, protein

from app.main.views.proteins.search import get_protein_metadata
from app.main.views.experiments import bp
from app.config import strings


def query_all(exp_id):
    protein_cnt, proteins = protein.get_proteins_by_experiment(exp_id)
    return proteins

@bp.route('/<experiment_id>/browse')
def browse(experiment_id):
    # species_list = [ species.name for species in taxonomies.getAllSpecies() ]
    # submitted, form_schema = search_view.build_schema(request, species_list)

    # pager = paginate.Paginator(form_schema, search_view.QUERY_PAGE_LIMIT)
    # pager.parse_parameters(request)

    user = current_user if current_user.is_authenticated else None
    exp = experiment.get_experiment_by_id(experiment_id, user)
    proteins = query_all(experiment_id)
    # proteins = []
    protein_metadata = {}
    # errors = []

    # if submitted:
    #     errors = search_view.build_validator(form_schema).validate()
    #     if len(errors) == 0:
    #         proteins = search_view.perform_query(form_schema, pager, experiment_id)
    # else:
    #     proteins = query_all(experiment_id, pager)

    for p in proteins:
        get_protein_metadata(p, protein_metadata, user, experiment_id)

    # form_renderer = forms.FormRenderer(form_schema)
    return render_template(
        'proteomescout/experiments/browse.html',
        title = strings.experiment_browse_page_title % (exp.name),
        experiment=exp,
        proteins=proteins,
        protein_metadata=protein_metadata,
        protein_zip=zip(proteins, protein_metadata),
    )

