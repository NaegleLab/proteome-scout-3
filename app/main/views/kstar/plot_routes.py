"""
KSTAR Plotting Routes Module

This module provides Flask route handlers for generating, updating, and exporting KSTAR dot plots
and integrated plots (with dendrograms). It processes input data files (activities and FPR),
applies filtering, sorting, and clustering based on user parameters, and renders
visualizations using Matplotlib.

Key features:
- Processing uploaded KSTAR activity and FPR CSV files
- Filtering kinases based on significance or manual selection
- Sorting kinases and samples (alphabetical, by activity, hierarchical clustering)
- Rendering dot plots with optional dendrograms for hierarchical clustering
- Exporting plots in various formats (PNG, PDF, SVG, etc.)
- Interactive updates based on user filtering/sorting selections

All routes handle errors by returning descriptive JSON responses.
"""

from flask import request, jsonify, send_file
import pandas as pd
import json
import logging
import matplotlib.pyplot as plt
from io import BytesIO

from app.main.views.kstar import bp
from app.main.views.kstar.utils import parse_bool, safe_json_loads, create_error_response, parse_comma_separated_list
from app.main.views.kstar.plotting import create_integrated_plot, create_dot_plot
from app.main.views.kstar.clustering import handle_clustering_for_plot
from app.main.views.kstar.data_processing import (
    process_activities_data,
    filter_significant_kinases,
    handle_kinase_filtering,
    handle_sample_filtering
)

from app.main.views.kstar.modules import (
    read_csv_file,
    extract_plot_params,
    extract_plot_settings,
    extract_dendrogram_settings,
    extract_custom_labels,
    apply_sorting,
    validate_files,
    validate_plot_parameters
)

logger = logging.getLogger(__name__)

@bp.route('/plot', methods=['POST'])
@validate_files
@validate_plot_parameters
def generate_plot():
    """
    Generate a custom dot plot or integrated plot from uploaded KSTAR data files.
    
    This endpoint handles the initial plot creation from uploaded activity and FPR files.
    It processes the raw data, applies filtering based on significance or manual selections,
    performs requested sorting or clustering, and creates the visualization.
    
    Request Parameters:
    - activitiesFile: CSV file containing kinase activity data
    - fprFile: CSV file containing FPR data
    - Various plot settings (colors, sizes, sorting options, etc.)
    
    Returns:
        JSON response containing:
        - plot: Base64-encoded plot image
        - log_results: JSON representation of the processed activity data
        - fpr_df: JSON representation of the processed FPR data
        - original_log_results: JSON of the unmodified activity data (for reset)
        - original_fpr_df: JSON of the unmodified FPR data (for reset)
        
        If an error occurs, returns an error JSON response with status code 500.
    """
    try:
        # Extract configuration parameters from the request
        plot_params = extract_plot_params()
        plot_settings = extract_plot_settings()
        sort_settings = {
            'kinases_mode': request.form.get('sortKinases', 'none'),
            'samples_mode': request.form.get('sortSamples', 'none')
        }
        
        # Extract dendrogram toggle settings
        dendrogram_settings = extract_dendrogram_settings()
        
        # Get the uploaded files
        activities_file = request.files.get('activitiesFile')
        fpr_file = request.files.get('fprFile')
        binary_evidence_file = request.files.get('binary_evidence')
        
        # Read the CSV data into dataframes
        activities_df = read_csv_file(activities_file)
        fpr_df = read_csv_file(fpr_file)
        binary_evidence_df = None  # Evidence functionality removed
        
        # Process the raw activities data (log transform, etc.)
        log_results = process_activities_data(activities_df)
        original_log_results = log_results.copy()
        original_fpr_df = fpr_df.copy()
        
        # Apply significance-based filtering if requested
        if parse_bool(request.form.get('restrictKinases', 'false')):
            log_results, fpr_df, binary_evidence_df = filter_significant_kinases(
                log_results, fpr_df, binary_evidence_df
            )
        
        # Apply manual kinase filtering if specified
        kinases_to_drop = parse_comma_separated_list(request.form.get('kinases_to_drop', ''))
        if kinases_to_drop:
            log_results = log_results.drop(index=kinases_to_drop, errors='ignore')
            fpr_df = fpr_df.drop(index=kinases_to_drop, errors='ignore')
            # Evidence filtering removed
        
        # Apply interactive kinase and sample filtering
        log_results, fpr_df, binary_evidence_df = handle_kinase_filtering(
            log_results, fpr_df, binary_evidence_df, request.form
        )
        log_results, fpr_df, binary_evidence_df = handle_sample_filtering(
            log_results, fpr_df, binary_evidence_df, request.form.get('manualSampleSelect', '')
        )
        
        # Apply sorting based on settings (alphabetical, activity level, etc.)
        log_results, fpr_df, binary_evidence_df = apply_sorting(log_results, fpr_df, binary_evidence_df, sort_settings)
        
        # Apply hierarchical clustering if requested, and get linkage matrices
        log_results, fpr_df, binary_evidence_df, row_linkage, col_linkage = handle_clustering_for_plot(
            log_results, fpr_df, binary_evidence_df, sort_settings, plot_params, dendrogram_settings
        )
        
        # Extract custom column labels if provided
        custom_xlabels = extract_custom_labels(log_results)
        use_integrated_plot = parse_bool(request.form.get('useIntegratedPlot', 'true'))
        
        # Create either an integrated plot (with dendrograms) or a simple dot plot
        if use_integrated_plot and (row_linkage is not None or col_linkage is not None):
            plot_img = create_integrated_plot(
                log_results, fpr_df, binary_evidence_df,
                row_linkage=row_linkage, col_linkage=col_linkage,
                binary_sig=(request.form.get('significantActivity', 'binary') == 'binary'),
                custom_xlabels=custom_xlabels, show_evidence=False,
                **plot_params, **plot_settings, **dendrogram_settings
            )
        else:
            plot_img = create_dot_plot(
                log_results, fpr_df, binary_evidence_df,
                binary_sig=(request.form.get('significantActivity', 'binary') == 'binary'),
                custom_xlabels=custom_xlabels, **plot_params, **plot_settings
            )
        
        # Return the plot and data as JSON
        return jsonify({
            "plot": plot_img,
            "log_results": log_results.to_json(),
            "fpr_df": fpr_df.to_json(),
            "original_log_results": original_log_results.to_json(),
            "original_fpr_df": original_fpr_df.to_json()
        })
    except Exception as e:
        logger.error("Error in generate_plot: %s", e, exc_info=True)
        return jsonify(create_error_response(e)), 500

@bp.route('/update_plot', methods=['POST'])
@validate_plot_parameters
def update_plot():
    """
    Update an existing plot based on new filtering, sorting, or visualization parameters.
    
    This endpoint is called when UI controls are adjusted for an existing plot.
    It reads the original data stored in the frontend form, applies the requested
    modifications, and returns an updated visualization without requiring new file uploads.
    
    Request Parameters:
    - original_log_results: JSON string of the original activity data
    - original_fpr_df: JSON string of the original FPR data
    - Various filtering and sorting parameters
    
    Returns:
        JSON response containing:
        - plot: Base64-encoded updated plot image
        - log_results: JSON representation of the modified activity data
        - fpr_df: JSON representation of the modified FPR data
        
        If an error occurs, returns an error JSON response with status code 500.
    """
    try:
        # Get the original data from the frontend form
        orig_log_json = request.form.get('original_log_results')
        orig_fpr_json = request.form.get('original_fpr_df')
        if not orig_log_json or not orig_fpr_json:
            raise ValueError("Original data missing. Please generate plot first.")
        
        # Parse JSON data back to DataFrames
        log_results = pd.read_json(orig_log_json)
        fpr_df = pd.read_json(orig_fpr_json)
        
        # Extract plot configuration parameters
        plot_params = extract_plot_params()
        plot_settings = extract_plot_settings()
        binary_sig = (request.form.get('significantActivity', 'binary') == 'binary')
        dendrogram_settings = extract_dendrogram_settings()
        
        # Apply kinase filtering (select or remove mode)
        kinase_edit_mode = request.form.get('manualKinaseEdit', 'none')
        selected_kinases = safe_json_loads(request.form.get('kinaseSelect', '[]'), [])
        if kinase_edit_mode == 'select' and selected_kinases:
            # Keep only the selected kinases
            log_results = log_results.loc[selected_kinases]
            fpr_df = fpr_df.loc[selected_kinases]
        elif kinase_edit_mode == 'remove' and selected_kinases:
            # Remove the selected kinases
            log_results = log_results.drop(selected_kinases, errors='ignore')
            fpr_df = fpr_df.drop(selected_kinases, errors='ignore')
        
        # Apply sample filtering
        selected_samples = safe_json_loads(request.form.get('sampleSelect', '[]'), [])
        if selected_samples:
            log_results = log_results[selected_samples]
            fpr_df = fpr_df[selected_samples]
        
        # Get custom column labels
        custom_xlabels = extract_custom_labels(log_results)
        
        # Configure sorting settings
        sort_settings = {
            'kinases_mode': request.form.get('sortKinases', 'none'),
            'samples_mode': request.form.get('sortSamples', 'none')
        }
        
        # Apply manual kinase ordering if requested
        if sort_settings.get('kinases_mode') == 'manual':
            manual_order = safe_json_loads(request.form.get('manualKinaseOrder', '[]'), [])
            if manual_order and all(k in log_results.index for k in manual_order):
                log_results = log_results.reindex(manual_order)
                fpr_df = fpr_df.reindex(manual_order)
        
        # Apply activity-based kinase sorting
        if sort_settings.get('kinases_mode', '').startswith('by_activity_'):
            ascending = sort_settings['kinases_mode'].endswith('_asc')
            if not log_results.empty:
                sample_to_sort_by = log_results.columns[0]
                log_results = log_results.sort_values(by=sample_to_sort_by, ascending=ascending)
                fpr_df = fpr_df.reindex(log_results.index)
                
        # Apply activity-based sample sorting
        if sort_settings.get('samples_mode', '').startswith('by_activity_'):
            ascending = sort_settings['samples_mode'].endswith('_asc')
            if not log_results.empty:
                kinase_to_sort_by = log_results.index[0]
                sorted_cols = log_results.loc[kinase_to_sort_by].sort_values(ascending=ascending).index
                log_results = log_results[sorted_cols]
                fpr_df = fpr_df[sorted_cols]
        
        # Apply hierarchical clustering if requested, and get linkage matrices
        log_results, fpr_df, _, row_linkage, col_linkage = handle_clustering_for_plot(
            log_results, fpr_df, None, sort_settings, plot_params, dendrogram_settings
        )
        
        # Determine whether to use integrated plot with dendrograms
        use_integrated_plot = parse_bool(request.form.get('useIntegratedPlot', 'true'))
        
        # Create either an integrated plot or a simple dot plot
        if use_integrated_plot and (row_linkage is not None or col_linkage is not None):
            plot_img = create_integrated_plot(
                log_results, fpr_df, None,
                row_linkage=row_linkage, col_linkage=col_linkage,
                binary_sig=binary_sig, custom_xlabels=custom_xlabels,
                show_evidence=False,
                **plot_params, **plot_settings, **dendrogram_settings
            )
        else:
            plot_img = create_dot_plot(
                log_results, fpr_df, binary_sig=binary_sig,
                custom_xlabels=custom_xlabels, **plot_params, **plot_settings
            )
        
        # Return the updated plot and data
        return jsonify({
            "plot": plot_img,
            "log_results": log_results.to_json(),
            "fpr_df": fpr_df.to_json()
        })
    except Exception as e:
        logger.error("Error in update_plot: %s", e, exc_info=True)
        return jsonify(create_error_response(e)), 500

@bp.route('/plot/download', methods=['POST'])
@validate_plot_parameters
def download_plot():
    """
    Generate a high-quality plot file for download in the specified format.
    
    This endpoint creates a plot based on the current state and sends it as a downloadable
    file in the requested format (PNG, PDF, SVG, etc.). It uses the same data and parameters
    as the currently displayed plot, but may render at a higher resolution or with 
    format-specific optimizations.
    
    Request Parameters:
    - log_results or original_log_results: JSON string of the activity data
    - fpr_df or original_fpr_df: JSON string of the FPR data
    - download_format: File format (png, pdf, svg, etc.)
    - file_name: Name for the downloaded file
    - dpi: Resolution for raster formats
    - Various plot settings (identical to update_plot)
    
    Returns:
        Flask send_file response with the plot file for download.
        If an error occurs, returns an error JSON response with status code 500.
    """
    try:
        # Get the current data from the form (current view state)
        current_log_json = request.form.get('log_results') or request.form.get('original_log_results')
        current_fpr_json = request.form.get('fpr_df') or request.form.get('original_fpr_df')
        if not current_log_json or not current_fpr_json:
            raise ValueError("Plot data missing. Please generate plot first.")

        # Parse JSON data back to DataFrames
        log_results = pd.read_json(current_log_json)
        fpr_df = pd.read_json(current_fpr_json)

        # Extract plot configuration parameters
        plot_params = extract_plot_params()
        plot_settings = extract_plot_settings()
        binary_sig = (request.form.get('significantActivity', 'binary') == 'binary')
        download_format = request.form.get('download_format', 'png')
        file_name = request.form.get('file_name', 'KSTAR_dotplot')
        dendrogram_settings = extract_dendrogram_settings()
        use_integrated_plot = parse_bool(request.form.get('useIntegratedPlot', 'true'))
        
        # Set evidence and context flags to False (feature removed)
        show_evidence = False
        add_additional_context = False

        # Configure sorting settings
        sort_settings = {
            'kinases_mode': request.form.get('sortKinases', 'none'),
            'samples_mode': request.form.get('sortSamples', 'none')
        }

        # Get custom column labels
        custom_xlabels = extract_custom_labels(log_results)

        # Apply filtering and sorting based on current UI state
        # (Similar to update_plot but using the current state data)
        kinase_edit_mode = request.form.get('manualKinaseEdit', 'none')
        selected_kinases = safe_json_loads(request.form.get('kinaseSelect', '[]'), [])
        if kinase_edit_mode == 'select' and selected_kinases:
            log_results = log_results.loc[selected_kinases]
            fpr_df = fpr_df.loc[selected_kinases]
        elif kinase_edit_mode == 'remove' and selected_kinases:
            log_results = log_results.drop(selected_kinases, errors='ignore')
            fpr_df = fpr_df.drop(selected_kinases, errors='ignore')
        
        selected_samples = safe_json_loads(request.form.get('sampleSelect', '[]'), [])
        if selected_samples:
            log_results = log_results[selected_samples]
            fpr_df = fpr_df[selected_samples]

        # Apply sorting based on settings
        log_results, fpr_df, _ = apply_sorting(log_results, fpr_df, None, sort_settings)

        # Apply hierarchical clustering if requested, and get linkage matrices
        log_results, fpr_df, _, row_linkage, col_linkage = handle_clustering_for_plot(
            log_results, fpr_df, None, sort_settings, plot_params, dendrogram_settings
        )

        # Create a Matplotlib figure object for the download
        if use_integrated_plot:
            fig = create_integrated_plot(
                log_results, fpr_df,
                row_linkage=row_linkage,  # Pass linkage matrices explicitly
                col_linkage=col_linkage,
                download=True,  # Flag to return Figure object rather than base64
                binary_sig=binary_sig,
                custom_xlabels=custom_xlabels,
                **plot_params, **plot_settings, **dendrogram_settings
            )
        else:
            # Create a simple dot plot
            fig = create_dot_plot(
                log_results,
                fpr_df,
                binary_sig=binary_sig,
                custom_xlabels=custom_xlabels,
                download=True,  # Flag to return Figure object rather than base64
                **plot_params, **plot_settings
            )

        # Save the figure to a BytesIO buffer in the requested format
        output = BytesIO()
        dpi = int(request.form.get('dpi', 300))  # Higher DPI for downloads
        bg_color = plot_params.get('background_color', '#ffffff')
        fig.savefig(output, format=download_format, dpi=dpi, bbox_inches='tight', facecolor=bg_color)
        plt.close(fig)  # Close the figure to free memory
        output.seek(0)  # Rewind the buffer

        # Define MIME types for different file formats
        mime_types = {
            'png': 'image/png', 'jpg': 'image/jpeg', 'pdf': 'application/pdf',
            'svg': 'image/svg+xml', 'eps': 'application/postscript', 'tif': 'image/tiff'
        }

        # Send the file as an attachment with the appropriate MIME type
        return send_file(
            output,
            mimetype=mime_types.get(download_format, 'application/octet-stream'),
            as_attachment=True,
            download_name=f"{file_name}.{download_format}"
        )

    except Exception as e:
        logger.error("Error in download_plot: %s", e, exc_info=True)
        return jsonify(create_error_response(e)), 500