"""
KSTAR Plot Configuration Module

This module provides helper functions and decorators for KSTAR visualization processing.
It centralizes common configuration extraction, data transformation, and validation 
logic used across the plotting workflow.

Functions:
    read_csv_file: Reads and parses CSV/TSV data files with appropriate separators
    extract_plot_params: Extracts figure dimensions and font size from request
    extract_plot_settings: Extracts color settings for plot elements
    extract_dendrogram_settings: Extracts dendrogram display preferences
    extract_custom_labels: Processes custom column labels if provided
    apply_sorting: Applies requested sorting strategies to data frames
    
Decorators:
    validate_files: Ensures required files are present with valid extensions
    validate_plot_parameters: Validates numeric and color parameters
"""

from typing import Dict, Any
from flask import request, jsonify
import pandas as pd
import numpy as np
import json
import logging
from functools import wraps
import matplotlib.pyplot as plt
from io import BytesIO
import os

from app.main.views.kstar.plotting import create_integrated_plot, create_dot_plot
from app.main.views.kstar.clustering import handle_clustering_for_plot
from app.main.views.kstar.data_processing import (
    process_activities_data,
    filter_significant_kinases,
    handle_kinase_filtering,
    handle_sample_filtering,
    validate_dataframe_compatibility
)
from app.main.views.kstar.utils import (
    parse_bool,
    get_sep,
    parse_form_data,
    safe_json_loads,
    create_error_response,
    DEFAULT_COLORS,
    DEFAULT_PLOT_PARAMS,
    ALLOWED_FILE_EXTENSIONS,
    FormDataValidator,
    parse_comma_separated_list
)

logger = logging.getLogger(__name__)

# --- Helper functions ---
def read_csv_file(file) -> pd.DataFrame:
    """
    Read a CSV/TSV file using the appropriate separator and index column.
    
    Parameters:
        file: File object from request.files
        
    Returns:
        Pandas DataFrame with data and proper index
    """
    sep = get_sep(file.filename)
    try:
        return pd.read_csv(file, sep=sep, index_col=0)
    except Exception:
        file.seek(0)
        df = pd.read_csv(file, nrows=5)
        if df.columns[0] == 'Unnamed: 0':
            file.seek(0)
            return pd.read_csv(file, index_col=0)
        return df

def extract_plot_params() -> Dict[str, Any]:
    """
    Extract figure dimensions and font size from request form.
    
    Returns:
        Dictionary with fig_width, fig_height, and fontsize parameters
    """
    return {
        'fig_width': parse_form_data(request.form, 'figureWidth', DEFAULT_PLOT_PARAMS['fig_width'], float),
        'fig_height': parse_form_data(request.form, 'figureHeight', DEFAULT_PLOT_PARAMS['fig_height'], float),
        'fontsize': parse_form_data(request.form, 'fontSize', DEFAULT_PLOT_PARAMS['fontsize'], float)
    }

def extract_plot_settings() -> Dict[str, Any]:
    """
    Extract color settings for plot elements from request form.
    
    Returns:
        Dictionary with background_color, activity_color, and other color settings
    """
    return {
        'background_color': request.form.get('backgroundColor', DEFAULT_COLORS['background']),
        'activity_color': request.form.get('activityColor', DEFAULT_COLORS['activity']),
        'noactivity_color': request.form.get('lackActivityColor', DEFAULT_COLORS['no_activity']),
        'kinases_dendrogram_color': request.form.get('kinases_dendrogram_color', '#000000'),
        'samples_dendrogram_color': request.form.get('samples_dendrogram_color', '#000000')  
    }

def extract_dendrogram_settings() -> Dict[str, bool]:
    """
    Extract dendrogram display preferences from request form.
    
    Returns:
        Dictionary with boolean flags for dendrogram display options
    """
    return {
        'show_kinases_dendrogram_inside': parse_bool(request.form.get('showKinasesDendrogramInside', 'false')),
        'show_samples_dendrogram': parse_bool(request.form.get('showSamplesDendrogram', 'true')),
    }

def extract_custom_labels(log_results: pd.DataFrame):
    """
    Process custom column labels if provided in the request.
    
    Parameters:
        log_results: DataFrame whose columns may need custom labels
        
    Returns:
        List of labels or None if no custom labels requested
    """
    if parse_bool(request.form.get('changeXLabel', 'false')):
        try:
            custom_labels = safe_json_loads(request.form.get('customXLabels', '{}'), {})
            return [custom_labels.get(col, col) for col in log_results.columns]
        except Exception as e:
            logger.warning("Error parsing custom labels: %s", e)
    return None

def apply_sorting(log_results: pd.DataFrame, fpr_df: pd.DataFrame, binary_evidence_df, sort_settings: Dict[str, str]):
    """
    Apply manual or activity-based sorting to the provided data frames.
    
    Parameters:
        log_results: Activity data DataFrame
        fpr_df: FPR data DataFrame
        binary_evidence_df: Evidence DataFrame (optional)
        sort_settings: Dictionary with sorting modes
        
    Returns:
        Tuple of sorted DataFrames (log_results, fpr_df, binary_evidence_df)
    """
    for mode_key, axis in [('kinases_mode', 0), ('samples_mode', 1)]:
        mode_value = sort_settings.get(mode_key, 'none')
        if mode_key == 'kinases_mode' and mode_value == 'manual':
            manual_order_json = request.form.get('manualKinaseOrder')
            if manual_order_json:
                try:
                    manual_order = json.loads(manual_order_json)
                    if manual_order and all(k in log_results.index for k in manual_order):
                        log_results = log_results.reindex(manual_order)
                        fpr_df = fpr_df.reindex(manual_order)
                        if binary_evidence_df is not None:
                            binary_evidence_df = binary_evidence_df.reindex(manual_order)
                except json.JSONDecodeError:
                    logger.error("Invalid manual kinase order JSON: %s", manual_order_json)
        elif mode_value.startswith('by_activity_'):
            ascending = mode_value.endswith('_asc')
            if axis == 0 and not log_results.empty:
                sort_by = log_results.columns[0]
                log_results = log_results.sort_values(by=sort_by, ascending=ascending)
                fpr_df = fpr_df.reindex(log_results.index)
                if binary_evidence_df is not None:
                    binary_evidence_df = binary_evidence_df.reindex(log_results.index)
            elif axis == 1 and not log_results.empty:
                sort_by = log_results.index[0]
                sorted_cols = log_results.loc[sort_by].sort_values(ascending=ascending).index
                log_results = log_results[sorted_cols]
                fpr_df = fpr_df[sorted_cols]
                if binary_evidence_df is not None:
                    binary_evidence_df = binary_evidence_df[sorted_cols]
    return log_results, fpr_df, binary_evidence_df

# --- Decorators ---
def validate_files(func):
    """
    Decorator to validate the presence and format of required uploaded files.
    
    Checks that both activities and FPR files are provided and have allowed extensions.
    
    Returns:
        Decorated function or error response
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        activities_file = request.files.get('activitiesFile')
        fpr_file = request.files.get('fprFile')
        if not activities_file or not fpr_file:
            return jsonify({"error": "Please provide both activities and FPR files."}), 400
        for file in [activities_file, fpr_file]:
            if not FormDataValidator.validate_file_extension(file.filename, ALLOWED_FILE_EXTENSIONS):
                return jsonify({
                    "error": f"Invalid file extension for {file.filename}. Allowed: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
                }), 400
        return func(*args, **kwargs)
    return wrapper

def validate_plot_parameters(func):
    """
    Decorator to validate numeric and color values in plot parameters.
    
    Ensures figure dimensions are positive numbers and colors are valid hex codes.
    
    Returns:
        Decorated function or error response
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        for param in ['figureWidth', 'figureHeight', 'fontSize']:
            value = request.form.get(param)
            if value and not FormDataValidator.validate_numeric(value, min_val=0):
                return jsonify({"error": f"Invalid {param}: must be a positive number"}), 400
        for param in ['backgroundColor', 'activityColor', 'lackActivityColor']:
            color = request.form.get(param)
            if color and not FormDataValidator.validate_color_hex(color):
                return jsonify({"error": f"Invalid color format for {param}: {color}"}), 400
        return func(*args, **kwargs)
    return wrapper