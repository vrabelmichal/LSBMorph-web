import argparse
from datetime import datetime
from astropy.table import Table
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# adjust this import if your Classification lives elsewhere
from models.galaxy import Classification, User  

def import_from_fits(db_url, input_fits, overwrite=False, user_id=None):
    """
    Reads classifications from a FITS table and updates/inserts into the DB.
    """
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    table = Table.read(input_fits, format='fits')

    with Session() as session:
        # determine user_id if not provided
        if user_id is None:
            first_user = session.query(User).first()
            if first_user is None:
                raise RuntimeError("No users in DB – create one or pass --user-id")
            user_id = first_user.id

        inserted = updated = skipped = 0
        for row in table:
            gid = row['ID']
            # lookup by user & galaxy
            obj = session.query(Classification).filter_by(
                user_id=user_id, galaxy_id=gid
            ).first()

            if obj is None:
                obj = Classification(user_id=user_id, galaxy_id=gid)
                session.add(obj)
                inserted += 1
            else:
                if overwrite:
                    updated += 1
                else:
                    print(f"Record {gid} exists. Use --overwrite to overwrite. Skipping.")
                    skipped += 1
                    continue

            obj.lsb_class           = int(row['Class'])
            obj.morphology          = int(row['Morphology'])
            obj.comments            = row['Comments'] or None
            obj.sky_bkg             = row['Sky_Bkg'] or None

            date_str = row['Date_of_classification']
            if date_str:
                obj.date_classified = datetime.strptime(date_str, "%Y/%m/%d-%H:%M")

            obj.awesome_flag        = int(row['AwesomeFlag'])
            obj.valid_redshift      = int(row['ValidRedshift'])
        session.commit()
    print(f"Done: inserted={inserted}, updated={updated}, skipped={skipped}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Import classification results from a FITS file into the DB"
    )
    p.add_argument(
        "--db-url",
        required=True,
        help="SQLAlchemy database URL (overrides FLASK config)"
    )
    p.add_argument(
        "--in",
        dest="input_fits",
        required=True,
        help="Path to input FITS file"
    )
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Update existing records instead of skipping them"
    )
    p.add_argument(
        "--user-id",
        type=int,
        help="User ID to assign classifications (defaults to first user in DB)"
    )
    args = p.parse_args()
    import_from_fits(
        args.db_url,
        args.input_fits,
        args.overwrite,
        args.user_id
    )