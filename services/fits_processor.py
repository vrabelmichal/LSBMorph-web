# services/fits_processor.py

import os
import numpy as np
from astropy.io import fits
from astropy.visualization import ZScaleInterval, AsinhStretch
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from PIL import Image
import shutil
import re

# Constants
ONE_JANSKY_ARCSEC_KIDS = 10 ** (0.4 * 23.9) / (0.2 ** 2)
OUTPUT_DPI = 100
Y_AXIS_RATIO = 0.9  # Same as original code

def ensure_dir(path):
    """Make sure directory exists"""
    if not os.path.exists(path):
        os.makedirs(path)

def get_image_filename(base_name, vmax_percentile, vmax_percentile_raw):
    """
    Generate the correct image filename based on the base name and vmax percentiles.
    Args:
        base_name: The base image name (e.g., 'masked_r_band')
        vmax_percentile: Percentile for masked/model/residual images
        vmax_percentile_raw: Percentile for raw image
    Returns: Filename string with appropriate suffix and .png extension
    """
    def slugify(value):
        return str(value).replace('.', 'p').replace('-', 'm')

    if base_name == "masked_r_band" or base_name == "galfit_model" or base_name == "residual":
        vmax_suffix = slugify(vmax_percentile)
        return f"{base_name}_vmax{vmax_suffix}.png"
    elif base_name == "raw_r_band":
        vmax_raw_suffix = slugify(vmax_percentile_raw)
        return f"{base_name}_vmax{vmax_raw_suffix}.png"
    else:
        return f"{base_name}.png"
    
def get_expected_vmax_percentile(base_name, default_vmax_percentile=99.0, default_vmax_percentile_raw=99.7):
    """
    Get the expected vmax percentile based on the base name.
    Args:
        base_name: The base image name (e.g., 'masked_r_band')
        default_vmax_percentile: Default value if not present in filename
        default_vmax_percentile_raw: Default value if not present in filename
    Returns: vmax_percentile, vmax_percentile_raw
    """
    if base_name == "masked_r_band" or base_name == "galfit_model" or base_name == "residual":
        return default_vmax_percentile
    elif base_name == "raw_r_band":
        return default_vmax_percentile_raw
    else:
        return None

    
def parse_image_filename(filename, default_vmax_percentile=99.0, default_vmax_percentile_raw=99.7):
    """
    Parse the image filename to extract base_name, vmax_percentile, and vmax_percentile_raw.
    Args:
        filename: The image filename (e.g., 'masked_r_band_vmax99p0.png')
        default_vmax_percentile: Default value if not present in filename
        default_vmax_percentile_raw: Default value if not present in filename
    Returns: (base_name, vmax_percentile, vmax_percentile_raw)
    """

    # Remove extension
    name = os.path.splitext(os.path.basename(filename))[0]

    # Patterns
    vmax_pattern = re.compile(r'^(.*)_vmax([0-9pm]+)$')
    # Try to match pattern with vmax
    m = vmax_pattern.match(name)
    if m:
        base_name = m.group(1)
        vmax_str = m.group(2)
        vmax_percentile = float(vmax_str.replace('p', '.').replace('m', '-'))
        if base_name == "raw_r_band":
            return base_name, default_vmax_percentile, vmax_percentile
        else:
            return base_name, vmax_percentile, default_vmax_percentile_raw
    else:
        # No vmax in filename, just base_name
        base_name = name
        return base_name, default_vmax_percentile, default_vmax_percentile_raw

    
def get_galaxy_images(galaxy_id, data_dirs=None, colors=None, add_titles=False, vmax_percentile=99.0, vmax_percentile_raw=99.7, session=None, galaxy_data=None):
    """
    Get paths to processed images for a galaxy.
    If images don't exist, generate them.
    
    Args:
        galaxy_id: ID of the galaxy
        data_dirs: Dictionary with paths to data directories
        colors: List of color settings [cmap, ellipse_color, redshift_color]
        add_titles: Boolean to add titles to images
        vmax_percentile: Percentile for masked/model/residual images
        vmax_percentile_raw: Percentile for raw image
        session: SQLAlchemy session for database access
        galaxy_data: Dictionary with galaxy parameters (if available)
    
    Returns: List of dictionaries with image info
    """
    if data_dirs is None:
        from flask import current_app
        data_dirs = {
            'output_dir': current_app.config['GALAXY_IMAGES_FOLDER'],
            'base_dir': current_app.config['DATA_BASE_DIR'],
        }
    
    if colors is None:
        colors = ['viridis', 'red', 'black']  # Default colors
    
    galaxy_dir = os.path.join(data_dirs['output_dir'], galaxy_id)

    ensure_dir(galaxy_dir)

    # List of base image names in order
    base_image_names = [
        "masked_r_band",
        "galfit_model",
        "residual",
        "raw_r_band",
        "aplpy",
        "lupton"
    ]

    expected_images = {
        name: get_image_filename(name, vmax_percentile, vmax_percentile_raw)
        for name in base_image_names
    }

    all_exist = all(os.path.exists(os.path.join(galaxy_dir, img)) for img in expected_images.values())
    
    generate_results = None

    if not all_exist:
        # Get galaxy data
        if galaxy_data is None:
            galaxy_data = get_galaxy_data(
                galaxy_id=galaxy_id,
                session=session
                )
        
        # Generate images
        generate_results = generate_galaxy_images(
            galaxy_id=galaxy_id,
            output_dir=galaxy_dir,
            galaxy=galaxy_data,
            data_dirs=data_dirs,
            colors=colors,
            add_titles=add_titles,
            vmax_percentile=vmax_percentile,
            vmax_percentile_raw=vmax_percentile_raw
        )
    
    # Return paths and titles
    titles = {
        "masked_r_band": 'Masked r-Band', 
        "galfit_model": 'GalfitModel', 
        "residual": 'Residual', 
        "raw_r_band": 'Raw r-band', 
        "aplpy": 'APLpy', 
        "lupton": 'Zoomed out'
    }
    
    return [
        {
            'path': f'galaxy_images/{galaxy_id}/{image_filename}', 
            'title': titles[image_base], 
            'base_name': image_base,
            'success': generate_results[image_base]['success'] if generate_results else True,
            'vmax': generate_results[image_base]['vmax'] if generate_results else get_expected_vmax_percentile(image_base, vmax_percentile, vmax_percentile_raw),
        }
        for image_base, image_filename in expected_images.items()
    ]

def galaxy_data_to_dict(galaxy):
    return {
        'ID': galaxy.id,
        'X': galaxy.x,
        'Y': galaxy.y,
        'RedshiftX': galaxy.redshift_x,
        'RedshiftY': galaxy.redshift_y,
        'r_r': galaxy.r_r,
        'q': galaxy.q,
        'PA': galaxy.pa,
        'Nucleus': galaxy.nucleus
    }

def get_galaxy_data(galaxy_id, session=None):
    """Get galaxy data from the database"""
    from models.galaxy import Galaxy
    from flask import current_app
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
    Session = sessionmaker(bind=engine)

    def fetch(session):
        galaxy = session.query(Galaxy).filter_by(id=galaxy_id).first()
        if not galaxy:
            raise ValueError(f"Galaxy {galaxy_id} not found in database")
        return galaxy_data_to_dict(galaxy)

    if session is None:
        with Session() as s:
            return fetch(s)
    else:
        return fetch(session)

def sad_emoji():
    """Generate a sad emoji for missing images"""
    return np.array([
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ])

def generate_galaxy_images(galaxy_id, output_dir, galaxy, data_dirs, colors, add_titles=False, vmax_percentile=99.0, vmax_percentile_raw=99.7):
    """
    Generate all six images for a galaxy and save them as PNG files
    
    Args:
        galaxy_id: Galaxy ID string
        output_dir: Directory to save images to
        galaxy: Dictionary with galaxy parameters
        data_dirs: Dictionary with paths to data directories
        colors: List of [cmap, ellipse_color, redshift_color]
    """
    base_dir = data_dirs['base_dir']
    
    # Determine component type based on nucleus
    if galaxy['Nucleus'] == 1:
        component_type = 'double_component'
    else:
        component_type = 'single_component'
    
    # Paths to FITS files
    imgblock_path = os.path.join(base_dir, 'r_imgblocks', component_type, f"imgblock_{galaxy_id}.fits")
    unmasked_imgblock_path = os.path.join(base_dir, 'r_imgblocks', f"{component_type}_unmasked", f"imgblock_{galaxy_id}.fits")
    mask_path = os.path.join(base_dir, 'masks_r', f"mask{galaxy_id}.fits")
    
    # Source paths for pre-generated color images
    aplpy_src = os.path.join(base_dir, 'color_images/aplpy', f"{galaxy_id}.png")
    lupton_src = os.path.join(base_dir, 'color_images/Lupton_RGB_Images', f"{galaxy_id}.png")
    
    # Destination paths for all images
    masked_band_dest = os.path.join(output_dir, get_image_filename('masked_r_band', vmax_percentile, vmax_percentile_raw))
    galfit_model_dest = os.path.join(output_dir, get_image_filename('galfit_model', vmax_percentile, vmax_percentile_raw))
    residual_dest = os.path.join(output_dir, get_image_filename('residual', vmax_percentile, vmax_percentile_raw))
    raw_band_dest = os.path.join(output_dir, get_image_filename('raw_r_band', vmax_percentile, vmax_percentile_raw))
    aplpy_dest = os.path.join(output_dir, get_image_filename('aplpy', vmax_percentile, vmax_percentile_raw))
    lupton_dest = os.path.join(output_dir, get_image_filename('lupton', vmax_percentile, vmax_percentile_raw))
    
    results = dict()
    
    # Check for available FITS data
    try:
        imgblock = fits.open(imgblock_path)
        
        # Get mask data
        try:
            mask_data = fits.getdata(mask_path)
        except Exception as e:
            print(f"Error loading mask file for {galaxy_id}: {e}")
            mask_data = np.zeros_like(imgblock[1].data)
        
        # Calculate masked image
        masked_data = imgblock[1].data * np.logical_not(mask_data) * ONE_JANSKY_ARCSEC_KIDS
        
        # Calculate contrast values for different image types
        vmax = np.percentile(masked_data, vmax_percentile)
        
        # Set image scaling
        vmax_values = [
            vmax,  # masked band
            vmax,  # galfit model
            vmax,  # residual
            np.percentile(imgblock[1].data * ONE_JANSKY_ARCSEC_KIDS, vmax_percentile_raw),  # raw band
            0,     # aplpy (not used)
            0      # lupton (not used)
        ]
        
        # Generate the FITS-based images
        for i, (base_name, dest_path, title, percentile) in enumerate([
            ('masked_r_band', masked_band_dest, 'Masked r-Band', vmax_percentile),
            ('galfit_model', galfit_model_dest, 'GalfitModel', vmax_percentile),
            ('residual', residual_dest, 'Residual', vmax_percentile),
            ('raw_r_band', raw_band_dest, 'Raw r-band', vmax_percentile_raw)
        ]):
            if i == 0:
                data = masked_data
            elif i == 1:
                data = imgblock[2].data * ONE_JANSKY_ARCSEC_KIDS
            elif i == 2:
                data = imgblock[3].data * ONE_JANSKY_ARCSEC_KIDS
            elif i == 3:
                data = imgblock[1].data * ONE_JANSKY_ARCSEC_KIDS
            
            fig = plt.figure(figsize=(6, 6*Y_AXIS_RATIO), dpi=OUTPUT_DPI)
            ax = fig.add_axes([0, 0, 1, 1])
            
            # Plot image
            im = ax.imshow(data, vmax=vmax_values[i], cmap=colors[0])
            
            # For masked image, also show mask contour
            if i == 0:
                cont = ax.contour(mask_data, [0.5], colors=[colors[2]], zorder=1)
                
            # Add ellipse for galaxy model
            ellipse = Ellipse(
                (galaxy['X'], galaxy['Y']),
                width=(galaxy['r_r'] * 2 / 0.2),
                height=(galaxy['r_r'] * 2 / 0.2) * galaxy['q'],
                angle=galaxy['PA'] + 90, linewidth=1.5,
                color=colors[1], fill=False, linestyle='-', label='Modelled galaxy'
            )
            ax.add_patch(ellipse)
            
            # Add redshift marker if available
            if i == 3:
                ax.plot(
                    [galaxy['X'], galaxy['RedshiftX']], 
                    [galaxy['Y'], galaxy['RedshiftY']], 
                    lw=2, ls='--', c=colors[2]
                )
                ax.scatter(
                    galaxy['RedshiftX'], 
                    galaxy['RedshiftY'], 
                    c=colors[2], marker='x', s=150
                )
            if add_titles:
                ax.set_title(title)
            ax.set_yticks([])
            ax.set_xticks([])
            ax.set_frame_on(False)
            
            # Save figure
            fig.savefig(dest_path, bbox_inches='tight', pad_inches=0)
            plt.close(fig)

            results[base_name] = dict(
                path=dest_path,
                title=title,
                vmax=percentile,
                success=True,
            )

        
    except Exception as e:
        print(f"Error processing FITS data for {galaxy_id}: {e}")
        # Create placeholder images for missing FITS data
        for base_name, dest_path in [
            ('masked_r_band', masked_band_dest),
            ('galfit_model', galfit_model_dest),
            ('residual', residual_dest),
            ('raw_r_band', raw_band_dest)
        ]:
            fig = plt.figure(figsize=(6, 6*Y_AXIS_RATIO), dpi=OUTPUT_DPI)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.imshow(sad_emoji(), cmap='binary')
            t = f"Missing FITS data\n{dest_path.split('/')[-1]}"
            ax.set_title(t)
            ax.set_yticks([])
            ax.set_xticks([])
            fig.savefig(dest_path, bbox_inches='tight')
            plt.close(fig)

            results[base_name] = dict(
                path=dest_path,
                title=t,
                vmax=0,
                success=False,
            )
    
    # Handle color images (copy from source if available, or create placeholder)
    try:
        if os.path.exists(aplpy_src):
            # If it's a PNG, flip up-down and save to destination
            with Image.open(aplpy_src) as img:
                flipped_img = img.transpose(Image.FLIP_TOP_BOTTOM)
                flipped_img.save(aplpy_dest)
        else:
            fig = plt.figure(figsize=(6, 6*Y_AXIS_RATIO), dpi=OUTPUT_DPI)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.imshow(sad_emoji(), cmap='binary')
            ax.set_title("APLpy color image not available")
            ax.set_yticks([])
            ax.set_xticks([])
            fig.savefig(aplpy_dest, bbox_inches='tight')
            plt.close(fig)

        results['aplpy'] = dict(
            path=aplpy_dest,
            title='APLpy',
            vmax=0,
            success=True,
        )
            
        if os.path.exists(lupton_src):
            # Copy directly
            shutil.copy(lupton_src, lupton_dest)
        else:
            fig = plt.figure(figsize=(6, 6*Y_AXIS_RATIO), dpi=OUTPUT_DPI)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.imshow(sad_emoji(), cmap='binary')
            ax.set_title("Lupton RGB image not available")
            ax.set_yticks([])
            ax.set_xticks([])
            fig.savefig(lupton_dest, bbox_inches='tight')
            plt.close(fig)

        results['lupton'] = dict(
            path=lupton_dest,
            title='Lupton RGB',
            vmax=0,
            success=True,
        )
            
    except Exception as e:
        print(f"Error handling color images for {galaxy_id}: {e}")
        # Create placeholders for both color images if there was an error
        for dest_path, title in [(aplpy_dest, "APLpy"), (lupton_dest, "Lupton RGB")]:
            fig = plt.figure(figsize=(6, 6*Y_AXIS_RATIO), dpi=OUTPUT_DPI)
            ax = fig.add_axes([0, 0, 1, 1])
            ax.imshow(sad_emoji(), cmap='binary')
            ax.set_title(f"{title} image error")
            ax.set_yticks([])
            ax.set_xticks([])
            fig.savefig(dest_path, bbox_inches='tight')
            plt.close(fig)
    
    return results

def get_galaxy_image_paths(galaxy_id, data_dirs=None, vmax_percentile=99.0, vmax_percentile_raw=99.7):
    """
    Return the expected image paths for a given galaxy, without creating the images.
    Args:
        galaxy_id: ID of the galaxy
        data_dirs: Dictionary with paths to data directories
        vmax_percentile: Percentile for masked/model/residual images
        vmax_percentile_raw: Percentile for raw image
    Returns: List of dictionaries with image info (path, title)
    """
    if data_dirs is None:
        from flask import current_app
        data_dirs = {
            'output_dir': current_app.config['GALAXY_IMAGES_FOLDER'],
        }

    galaxy_dir = os.path.join(data_dirs['output_dir'], galaxy_id)

    base_image_names = [
        "masked_r_band",
        "galfit_model",
        "residual",
        "raw_r_band",
        "aplpy",
        "lupton"
    ]
    expected_images = {
        name: os.path.join(galaxy_dir, get_image_filename(name, vmax_percentile, vmax_percentile_raw))
        for name in base_image_names
    }
    return expected_images
