from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

import config
from models.galaxy import Galaxy, Classification, User, SkippedGalaxy
from services.fits_processor import get_galaxy_images, get_galaxy_image_paths, parse_image_filename, galaxy_data_to_dict
import os
from datetime import datetime
import random
import re
import unicodedata

app = Flask(__name__)
app.config.from_object(config)


# Set up SQLAlchemy engine and session
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'], echo=True)
Session = scoped_session(sessionmaker(bind=engine))

# Create tables if they don't exist
Galaxy.metadata.create_all(engine)
Classification.metadata.create_all(engine)
User.metadata.create_all(engine)

CLASSIFY_PARAM_DEFAULTS = {
    'with_redshift': None,
    'classified': False,
    'skipped': False,
    'valid_redshift': None
}

def get_classify_mode_params_from_request():
    params = {
        'with_redshift': CLASSIFY_PARAM_DEFAULTS['with_redshift'],
        'valid_redshift': CLASSIFY_PARAM_DEFAULTS['valid_redshift'],
        'classified': CLASSIFY_PARAM_DEFAULTS['classified'],
        'skipped': CLASSIFY_PARAM_DEFAULTS['skipped']
    }
    
    # Process all boolean parameters in a consistent way
    for param_name in params:
        param_value = request.args.get(param_name)
        if param_value and param_value.lower() in ('yes', 'true'):
            params[param_name] = True
        elif param_value and param_value.lower() in ('no', 'false'):
            params[param_name] = False
    return params

def classify_mode_params_to_url_values(query_params):
    redirect_args = {
        p: ('yes' if v else 'no')
        for p, v in query_params.items()
        if v is not None and v != CLASSIFY_PARAM_DEFAULTS[p]
    }
    return redirect_args

@app.teardown_appcontext
def remove_session(exception=None):
    Session.remove()


@app.route('/')
def index():
    """Home page with login form"""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
)


@app.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    username = request.form['username']
    clean_username = (
        unicodedata.normalize('NFKD', username)
        .encode('ascii', 'ignore')
        .decode('ascii')
    )
    clean_username = re.sub(r'\W+', '', clean_username).strip().lower()  # Remove non-alphanumeric
    session['username'] = clean_username
    
    with Session() as db_session:
        # Check if user exists, create if not
        user = User.get_or_create(db_session, clean_username)
        session['user_id'] = user.id
    
    return redirect(url_for('classify'))


@app.route('/logout')
def logout():
    """Logout the user"""
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/classify')
def classify():
    """Main classification interface"""
    if 'username' not in session:
        return redirect(url_for('index'))

    # Process URL parameters using the defaults
    params = get_classify_mode_params_from_request()
        
    with Session() as db_session: 
        # Get a galaxy to classify (either next in sequence or random)
        galaxy_id = request.args.get('id')

        if galaxy_id:
            # Convert 'p' to '+' in galaxy ID if needed
            pattern = r'^(KiDSDR4_J\d{6}\.\d{3})([p])(\d{6}\.\d{2})$'
            m = re.match(pattern, galaxy_id)
            if m:
                galaxy_id = m.group(1) + '+' + m.group(3)
        
        if not galaxy_id:
            galaxy = Galaxy.get_next_for_user(
                session=db_session,
                user_id=session['user_id'],
                current_galaxy_id=None,
                **params
            )
        else:
            galaxy = Galaxy.get_by_id(
                session=db_session, 
                galaxy_id=galaxy_id
            )
        if not galaxy:
            return render_template('galaxy_not_found.html')

        current_classification = db_session.query(Classification).filter_by(
            user_id=session['user_id'],
            galaxy_id=galaxy.id
        ).first()
        next_galaxy = Galaxy.get_next_for_user(
            session=db_session,
            user_id=session['user_id'],
            current_galaxy_id=galaxy.id,
            skipped=params['skipped'],
            classified=None,  # This has to be None for performance reasons
            with_redshift=params['with_redshift'],
            valid_redshift=params['valid_redshift'],
        )
        previous_galaxy = Galaxy.get_previous_for_user(
            session=db_session,
            user_id=session['user_id'],
            current_galaxy_id=galaxy.id,
            skipped=params['skipped'],
            classified=None,  # This has to be None for performance reasons
            with_redshift=params['with_redshift'],
            valid_redshift=params['valid_redshift'],
        )
        # Get image paths for this galaxy
        image_paths = get_galaxy_images(
            galaxy_id=galaxy.id,
            data_dirs={
                'output_dir': app.config['GALAXY_IMAGES_FOLDER'],
                'base_dir': app.config['DATA_BASE_DIR'],
            },
            vmax_percentile=config.VMAX_PERCENTILE,
            vmax_percentile_raw=config.VMAX_PERCENTILE_RAW,
            session=None,
            galaxy_data=galaxy_data_to_dict(galaxy),
            )
        
        # Calculate progress
        progress = Classification.get_progress(db_session, session['user_id'])
        
        return render_template(
            'classify.html', 
            galaxy=galaxy,
            next_galaxy=next_galaxy,
            previous_galaxy=previous_galaxy,
            image_paths=image_paths,
            progress=progress,
            current_classification=current_classification,
            with_redshift=params['with_redshift'],
            classified=params['classified'],
            skipped=params['skipped'],
            valid_redshift=params['valid_redshift'],
            )


@app.route('/static/galaxy_images/<galaxy_id>/<image_file>')
def serve_galaxy_image(galaxy_id, image_file):
    """Serve a galaxy image file with optional vmax_percentile parameters"""
    
    base_name, vmax_percentile, vmax_percentile_raw = parse_image_filename(
        filename=image_file,
        default_vmax_percentile=config.VMAX_PERCENTILE,
        default_vmax_percentile_raw=config.VMAX_PERCENTILE_RAW,
    )
    
    image_paths = get_galaxy_image_paths(
        galaxy_id,
        data_dirs={
            'output_dir': app.config['GALAXY_IMAGES_FOLDER'],
            'base_dir': app.config['DATA_BASE_DIR'],
        },
        vmax_percentile=vmax_percentile,
        vmax_percentile_raw=vmax_percentile_raw,
    )
    image_path = image_paths.get(base_name)
    if not image_path:
        # return 404 if the image file is not found
        return jsonify({'error': 'Image not found'}), 404

    # If the image doesn't exist yet, generate it
    if not os.path.exists(image_path):
        data_dirs = {
            'output_dir': app.config['GALAXY_IMAGES_FOLDER'],
            'base_dir': app.config['DATA_BASE_DIR'],
        }
        get_galaxy_images(
            galaxy_id,
            data_dirs=data_dirs,
            vmax_percentile=vmax_percentile,
            vmax_percentile_raw=vmax_percentile_raw
        )
    
    # Serve the image file
    return send_from_directory(os.path.dirname(image_path), os.path.basename(image_path))

@app.route('/submit_classification', methods=['POST'])
def submit_classification():
    """Save classification data"""
    # Extract form data
    galaxy_id = request.form.get('galaxy_id')
    raw_lsb = request.form.get('lsb_class')
    raw_morph = request.form.get('morphology')
    comments = request.form.get('comments', '')
    awesome_flag = 'awesome_flag' in request.form
    valid_redshift = 'valid_redshift' in request.form
    
    # Extract query parameters
    params = get_classify_mode_params_from_request()
    base_redirect_args = classify_mode_params_to_url_values(params)


    errors = []
    # Validate lsb_class
    try:
        lsb_class = int(raw_lsb)
        if lsb_class not in (-1, 0, 1):
            errors.append('lsb_class')
    except (TypeError, ValueError):
        errors.append('lsb_class')

    # Validate morphology
    try:
        morphology = int(raw_morph)
        if morphology not in (-1, 0, 1, 2):
            errors.append('morphology')
    except (TypeError, ValueError):
        errors.append('morphology')

    # If any validation failed, redirect back with error info in query string
    if errors:
        redirect_args = {'id': galaxy_id, 'errors': ','.join(errors)}
        redirect_args.update(base_redirect_args)
        return redirect(url_for('classify', **redirect_args))
    
    with Session() as db_session:
        # Save to database
        Classification.create_or_update(
            session=db_session,
            user_id=session['user_id'],
            galaxy_id=galaxy_id,
            lsb_class=lsb_class,
            morphology=morphology,
            comments=comments,
            awesome_flag=awesome_flag,
            valid_redshift=valid_redshift,
        )
        db_session.commit()
        
        next_galaxy = Galaxy.get_next_for_user(
            session=db_session,
            user_id=session['user_id'], 
            current_galaxy_id=galaxy_id,
            with_redshift=params['with_redshift'],
            classified=params['classified'],
            skipped=params['skipped'],
            valid_redshift=params['valid_redshift'],
        )
        next_galaxy_id = next_galaxy.id if next_galaxy else None

    redirect_args = dict(base_redirect_args)
    if next_galaxy_id:
        redirect_args['id'] = next_galaxy_id

    return redirect(url_for('classify', **redirect_args))


@app.route('/skip_galaxy', methods=['GET'])
def skip_galaxy():
    """Skip the current galaxy and record the reason"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    # Extract form data
    galaxy_id = request.args.get('id')
    comments = request.form.get('comments', '')
    
    # Get query parameters to preserve for next redirect
    params = get_classify_mode_params_from_request()
    
    with Session() as db_session:
        # Save to database
        SkippedGalaxy.create_or_update(
            session=db_session,
            user_id=session['user_id'],
            galaxy_id=galaxy_id,
            comments=comments
        )
        db_session.commit()

        next_galaxy = Galaxy.get_next_for_user(
            session=db_session,
            user_id=session['user_id'], 
            current_galaxy_id=galaxy_id,
            with_redshift=params['with_redshift'],
            classified=params['classified'],
            skipped=params['skipped'],
            valid_redshift=params['valid_redshift'],
        )
        next_galaxy_id = next_galaxy.id if next_galaxy else None

    # Redirect to next galaxy, preserving query parameters
    redirect_args = classify_mode_params_to_url_values(params)
    if next_galaxy_id:
        redirect_args['id'] = next_galaxy_id
        
    return redirect(url_for('classify', **redirect_args))


@app.route('/skipped_galaxies')
def skipped_galaxies():
    """Show skipped galaxies"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    with Session() as db_session:
        # Get skipped galaxies for the user
        skipped_galaxies = SkippedGalaxy.get_skipped(db_session, session['user_id'])
        
        return render_template('skipped_galaxies.html', skipped_galaxies=skipped_galaxies)


@app.route('/unskip_galaxy', methods=['POST'])
def unskip_galaxy():
    """Unskip a galaxy"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    # Extract form data
    galaxy_id = request.form['galaxy_id']
    
    with Session() as db_session:
        # Remove the skipped galaxy record
        SkippedGalaxy.delete_skipped(db_session, session['user_id'], galaxy_id)
        db_session.commit()
    
    # Redirect to skipped galaxies page
    return redirect(url_for('skipped_galaxies'))


@app.route('/help')
def help():
    """Help page with examples and tips"""
    category = request.args.get('category', 'examples')
    
    # Get all image names from examples directory
    examples_dir = os.path.join(app.config['EXAMPLES_IMAGES_FOLDER'], )
    example_images = []
    
    if os.path.exists(examples_dir):
        # Get image files with natural sorting of numeric parts (e.g., example1.png, example2.png, example10.png)
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() 
                for text in re.split(r'(\d+)', s)]
        
        example_images = [f for f in os.listdir(examples_dir) 
                 if os.path.isfile(os.path.join(examples_dir, f)) 
                 and f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        example_images.sort(key=natural_sort_key)
    
    return render_template('help.html', category=category, example_images=example_images, example_descriptions=dict())


@app.route('/results')
def results():
    """Show results/statistics for the current user"""
    if 'username' not in session:
        return redirect(url_for('index'))
    
    with Session() as db_session:
        # Get classification statistics for the user
        user_stats = Classification.get_stats_for_user(db_session, session['user_id'])

        return render_template('results.html', stats=user_stats)


@app.route('/aladin/<ra>/<dec>')
def aladin(ra, dec):
    """Open Aladin viewer in a new tab"""
    aladin_url = f"https://aladin.unistra.fr/AladinLite/?target={ra} {dec}&fov=0.1"
    return render_template('aladin.html', aladin_url=aladin_url)

if __name__ == '__main__':
    app.run(debug=True)

