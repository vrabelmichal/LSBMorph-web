import os
import argparse
from datetime import datetime
from astropy.table import Table
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# adjust this import to point at your actual model
from models.galaxy import Classification  

# constant for all rows
SKY_BKG = "masked"

def export_to_fits(db_url, output_fits, overwrite=False):
    """
    Connects to the database, fetches all Classification rows,
    and writes them to output_fits as a FITS table.
    """
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        records = session.query(Classification).all()

    # prepare columns
    ids = []
    classes = []
    morphs = []
    comments = []
    dates = []
    awesome = []
    validz = []

    for r in records:
        ids.append(str(r.id))
        classes.append(int(r.lsb_class))           # or r.classification_field
        morphs.append(int(r.morphology))
        comments.append(r.comments or "")
        dates.append(
            r.date_classified.isoformat()
            if hasattr(r, "date_of_classification") else ""
        )
        awesome.append(int(r.awesome_flag))
        validz.append(int(r.valid_redshift))

    table = Table(
        [ids, classes, morphs, comments,
         [SKY_BKG]*len(ids), dates, awesome, validz],
        names=["ID", "Class", "Morphology", "Comments",
               "Sky_Bkg", "Date_of_classification",
               "AwesomeFlag", "ValidRedshift"],
        dtype=["U20", "i8", "i8", "U200", "U10", "U25", "i8", "i8"]
    )

    # check for existing file
    if os.path.exists(output_fits) and not overwrite:
        print(f"Output file '{output_fits}' already exists. Use --overwrite to overwrite.")
        return

    table.write(output_fits, format="fits", overwrite=overwrite)
    print(f"Wrote {len(ids)} records to {output_fits} (overwrite={overwrite})")

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Export classification table to a FITS file"
    )
    p.add_argument(
        "--db-url",
        help="SQLAlchemy database URL (overrides FLASK config)",
        required=True
    )
    p.add_argument(
        "--out",
        help="Path to output FITS file",
        default="classifications.fits"
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing FITS file if it exists"
    )
    args = p.parse_args()
    export_to_fits(args.db_url, args.out, args.overwrite)
