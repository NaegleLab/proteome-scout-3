import sys
import os
from flask_sqlalchemy import SQLAlchemy
import csv

# Allows for the importing of modules from the proteomescout-3 app within the script
#SCRIPT_DIR = '/Users/saqibrizvi/Documents/NaegleLab/ProteomeScout-3/proteomescout-3'
SCRIPT_DIR = '/Users/kmn4mj/GIT/public/proteome-scout-3'
sys.path.append(SCRIPT_DIR)

SCRIPT_DIR2 = '/Users/kmn4mj/GIT/public/proteome-scout-3/scripts/schema'
sys.path.append(SCRIPT_DIR2)


from scripts.app_setup import create_app
from scripts.progressbar import ProgressBar
from app.utils.export_proteins import *
from app.database import protein, modifications, experiment
from app.utils.downloadutils import experiment_metadata_to_tsv, zip_package

from FlaskSchemaReporter import FlaskSchemaReporter

# directory variable to be imported
OUTPUT_DIR = "scripts/output"

# database instantiated for the script
db = SQLAlchemy()

# application created within which the script can be run
app = create_app()
# database linked to the app
db.init_app(app)

with app.app_context():
    reporter = FlaskSchemaReporter(app=app, db=db)
    reporter.extract_all_schema_info()
    reporter.print_summary()  # Console output
    #reporter.generate_csv_reports("my_schema")  # CSV files
    reporter.generate_json_report(OUTPUT_DIR+"/test_schema.json")  # JSON file