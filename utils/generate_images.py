#!/usr/bin/env python3
# generate_all_galaxy_images.py
# Generate images for all galaxies in the database using default percentile settings

import os
import sys
import time
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add web directory to path if needed
script_dir = os.path.dirname(os.path.abspath(__file__))
web_dir = os.path.join(os.path.dirname(script_dir), 'web')
if web_dir not in sys.path:
    sys.path.append(web_dir)

# Import from web application
import config
from models.galaxy import Galaxy
from services.fits_processor import (
    get_galaxy_images, get_image_filename, galaxy_data_to_dict
)


def setup_database_session_class():
    """Establish a connection to the database and return a session"""
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    Session = scoped_session(sessionmaker(bind=engine))
    return Session


def get_all_galaxy_ids(db_session):
    """Retrieve all galaxy IDs from the database"""
    return [galaxy.id for galaxy in db_session.query(Galaxy.id).all()]


def check_existing_images(galaxy_id, output_dir, vmax_percentile, vmax_percentile_raw):
    """Check if images already exist for this galaxy with these settings"""
    base_image_names = [
        "masked_r_band", "galfit_model", "residual", 
        "raw_r_band", "aplpy", "lupton"
    ]
    
    galaxy_dir = os.path.join(output_dir, galaxy_id)
    
    if not os.path.exists(galaxy_dir):
        return False
    
    expected_images = {
        name: get_image_filename(name, vmax_percentile, vmax_percentile_raw)
        for name in base_image_names
    }
    
    all_exist = all(os.path.exists(os.path.join(galaxy_dir, img)) 
                   for img in expected_images.values())
    return all_exist


def process_galaxy(galaxy_data, data_dirs, vmax_percentile, vmax_percentile_raw, force=False):
    """Process a single galaxy and generate its images"""
    try:
        galaxy_id = galaxy_data['ID']
        galaxy_dir = os.path.join(data_dirs['output_dir'], galaxy_id)
        
        # Check if images already exist
        if not force and check_existing_images(
            galaxy_id, data_dirs['output_dir'], 
            vmax_percentile, vmax_percentile_raw
        ):
            return galaxy_id, True, "Already exists"
        
        # Make sure the directory exists
        os.makedirs(galaxy_dir, exist_ok=True)
        
        # Generate images
        get_galaxy_images(
            galaxy_id=galaxy_id,
            data_dirs=data_dirs,
            vmax_percentile=vmax_percentile,
            vmax_percentile_raw=vmax_percentile_raw,
            galaxy_data=galaxy_data,
            session=None,
        )
        return galaxy_id, True, "Generated"
    except Exception as e:
        return galaxy_id, False, str(e)

def main(num_workers=1, vmax_percentile=99.0, vmax_percentile_raw=99.7, force=False):
    """Main function to orchestrate the process"""
    print(f"Starting image generation with {num_workers} workers")
    print(f"Using vmax_percentile={vmax_percentile}, vmax_percentile_raw={vmax_percentile_raw}")
    
    # Setup data directories
    data_dirs = {
        'output_dir': config.GALAXY_IMAGES_FOLDER,
        'base_dir': config.DATA_BASE_DIR,
    }
    
    # Setup database session
    Session = setup_database_session_class()
    with Session() as db_session:
        # Fetch full Galaxy objects and convert to dicts
        galaxies = db_session.query(Galaxy).all()
        galaxy_data_list = [galaxy_data_to_dict(g) for g in galaxies]
        total_galaxies = len(galaxy_data_list)
        print(f"Found {total_galaxies} galaxies in the database")
    
    # Process galaxies
    start_time = time.time()
    processed = errors = skipped = 0
    
    if num_workers > 1:
        # Use multiprocessing for faster processing
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(
                    process_galaxy,
                    galaxy_data,
                    data_dirs,
                    vmax_percentile,
                    vmax_percentile_raw,
                    force
                ): galaxy_data['ID']
                for galaxy_data in galaxy_data_list
            }
            for future in as_completed(futures):
                galaxy_id, success, message = future.result()
                processed += 1
                if not success:
                    errors += 1
                    print(f"Error processing {galaxy_id}: {message}")
                elif message == "Already exists":
                    skipped += 1
                if processed % 10 == 0 or processed == total_galaxies:
                    elapsed = time.time() - start_time
                    progress = processed / total_galaxies * 100
                    print(f"Progress: {processed}/{total_galaxies} "
                          f"({progress:.2f}%) – Generated: {processed - errors - skipped}, "
                          f"Skipped: {skipped}, Errors: {errors}, Elapsed: {elapsed:.2f}s")
    else:
        # Single‑threaded processing
        for galaxy_data in galaxy_data_list:
            _, success, message = process_galaxy(
                galaxy_data,
                data_dirs,
                vmax_percentile,
                vmax_percentile_raw,
                force
            )
            processed += 1
            if not success:
                errors += 1
                print(f"Error processing {galaxy_data['ID']}: {message}")
            elif message == "Already exists":
                skipped += 1
            if processed % 10 == 0 or processed == total_galaxies:
                elapsed = time.time() - start_time
                progress = processed / total_galaxies * 100
                print(f"Progress: {processed}/{total_galaxies} "
                      f"({progress:.2f}%) – Generated: {processed - errors - skipped}, "
                      f"Skipped: {skipped}, Errors: {errors}, Elapsed: {elapsed:.2f}s")
    
    # Final report
    total_time = time.time() - start_time
    print(f"\nImage generation complete!")
    print(f"Total: {total_galaxies} galaxies")
    print(f"Generated: {processed - errors - skipped}")
    print(f"Skipped (already exist): {skipped}")
    print(f"Errors: {errors}")
    print(f"Time: {total_time:.2f} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images for all galaxies in the database")
    parser.add_argument('--workers', type=int, default=1, 
                        help="Number of worker processes to use")
    parser.add_argument('--vmax', type=float, default=99.0, 
                        help="vmax percentile for masked/model/residual images")
    parser.add_argument('--vmax-raw', type=float, default=99.7, 
                        help="vmax percentile for raw images")
    parser.add_argument('--force', action='store_true', 
                        help="Force regeneration of existing images")
    args = parser.parse_args()
    
    main(
        num_workers=args.workers, 
        vmax_percentile=args.vmax, 
        vmax_percentile_raw=args.vmax_raw,
        force=args.force
    )