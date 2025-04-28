from models.galaxy import Base, Galaxy, User, Classification
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import SQLALCHEMY_DATABASE_URI
import os
from astropy.io import fits
import argparse

def init_db():
    """Initialize the database schema"""
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)
    print("Database tables created.")

def load_galaxies_from_fits(fits_path):
    """Load galaxy data from FITS catalog into the database"""
    if not os.path.exists(fits_path):
        print(f"Error: FITS file not found at {fits_path}")
        return
    
    try:
        with fits.open(fits_path) as hdul:
            data = hdul[1].data
            
            engine = create_engine(SQLALCHEMY_DATABASE_URI)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Count galaxies before insertion
            existing_count = session.query(Galaxy).count()
            
            # Process each galaxy in the FITS file
            count = 0

            # Presuming that the data is already in the correct order
            sorted_data = data

            num_rows = len(sorted_data)

            # Get column names from the header
            column_names = data.columns.names

            # First, collect all IDs for mapping
            ids = [row['ID'] for row in sorted_data]

            for idx, row in enumerate(sorted_data):
                prev_id = ids[idx - 1] if idx > 0 else None
                next_id = ids[idx + 1] if idx < num_rows - 1 else None

                galaxy = Galaxy(
                    id=row['ID'],
                    ra=row['ra'],
                    dec=row['dec'],
                    x=row['X'],
                    y=row['Y'],
                    redshift_x=row['RedshiftX'] if 'RedshiftX' in column_names else None,
                    redshift_y=row['RedshiftY'] if 'RedshiftY' in column_names else None,
                    r_r=row['r_r'],
                    q=row['q'],
                    pa=row['PA'],
                    nucleus=bool(row['Nucleus']) if 'Nucleus' in column_names else False,
                    previous_id=prev_id,
                    next_id=next_id,
                )

                # Check if galaxy already exists
                existing = session.query(Galaxy).filter_by(id=galaxy.id).first()
                if not existing:
                    session.add(galaxy)
                    count += 1

                # Commit in batches to avoid memory issues
                if count % 100 == 0:
                    session.commit()
            
            # Final commit
            session.commit()
            
            # Count galaxies after insertion
            new_count = session.query(Galaxy).count()
            
            print(f"Successfully imported {count} new galaxies.")
            print(f"Database now contains {new_count} galaxies (was {existing_count}).")
            
    except Exception as e:
        print(f"Error loading galaxies: {e}")
        # print whole traceback
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Initialize database and load galaxy data')
    parser.add_argument('--fits', help='Path to FITS catalog to import')
    args = parser.parse_args()
    
    init_db()
    
    if args.fits:
        load_galaxies_from_fits(args.fits)
