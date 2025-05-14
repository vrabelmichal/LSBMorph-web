from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    
    classifications = relationship("Classification", back_populates="user")
    skipped_galaxies = relationship("SkippedGalaxy", back_populates="user")
    
    @classmethod
    def get_or_create(cls, session, username):
        """Get user by username or create if not exists"""
        user = session.query(cls).filter_by(username=username).first()
        if not user:
            user = cls(username=username)
            session.add(user)
            session.commit()
        return user
    
    @classmethod
    def get_by_id(cls, session, user_id):
        """Get user by ID"""
        return session.query(cls).filter(cls.id == user_id).first()
    

class Galaxy(Base):
    __tablename__ = 'galaxies'
    
    id = Column(String, primary_key=True)  # Galaxy ID from catalog
    ra = Column(Float, nullable=False)
    dec = Column(Float, nullable=False)
    x = Column(Float)  # Pixel coordinates 
    y = Column(Float)
    redshift_x = Column(Float, nullable=True)
    redshift_y = Column(Float, nullable=True)
    r_r = Column(Float)  # Radius
    q = Column(Float)    # Axis ratio
    pa = Column(Float)   # Position angle
    nucleus = Column(Boolean)  # 1 if galaxy has nucleus
    previous_id = Column(String, ForeignKey('galaxies.id'), nullable=True)
    next_id = Column(String, ForeignKey('galaxies.id'), nullable=True)
    
    # Fixed relationship setup for circular self-referencing
    previous = relationship(
        "Galaxy", 
        primaryjoin="Galaxy.previous_id==Galaxy.id",
        foreign_keys=[previous_id],
        uselist=False,
        remote_side=[id],
        back_populates="next_referring"
    )
    
    next = relationship(
        "Galaxy",
        primaryjoin="Galaxy.next_id==Galaxy.id", 
        foreign_keys=[next_id],
        uselist=False,
        remote_side=[id],
        back_populates="previous_referring"
    )
    
    # Relationships for the reverse direction
    next_referring = relationship(
        "Galaxy",
        primaryjoin="Galaxy.id==Galaxy.previous_id",
        foreign_keys="[Galaxy.previous_id]",
        uselist=False,
        back_populates="previous"
    )
    
    previous_referring = relationship(
        "Galaxy",
        primaryjoin="Galaxy.id==Galaxy.next_id",
        foreign_keys="[Galaxy.next_id]",
        uselist=False,
        back_populates="next"
    )
    
    classifications = relationship("Classification", back_populates="galaxy")
    skipped_galaxies = relationship("SkippedGalaxy", back_populates="galaxy")

    @classmethod
    def get_next_for_user(cls, session, user_id, current_galaxy_id=None, skipped=False, classified=False, 
                          with_redshift=None, valid_redshift=None, lsb_class=None, morphology=None):
        """Get next galaxy for user, filtering by skipped and classified status"""
        if current_galaxy_id:
            # Start from the galaxy specified by current_galaxy_id
            current_galaxy = session.query(cls).filter_by(id=current_galaxy_id).first()
            
            if not current_galaxy:
                return None  # Specified galaxy not found
            
            # Set to track visited galaxies to avoid cycles
            visited_ids = set([current_galaxy.id])
            
            # Hop forward through the galaxy chain
            while current_galaxy and current_galaxy.next and current_galaxy.next.id not in visited_ids:
                current_galaxy = current_galaxy.next
                
                if not current_galaxy:
                    break
                    
                visited_ids.add(current_galaxy.id)
                
                if skipped is not None:
                    # Check if this galaxy meets our skipped criteria
                    skipped_galaxy = session.query(SkippedGalaxy).filter_by(
                        user_id=user_id, galaxy_id=current_galaxy.id
                    ).first()
                    
                    if (skipped and not skipped_galaxy) or (not skipped and skipped_galaxy):
                        continue  # Skip this galaxy if it doesn't match skipped criteria
                
                classified_galaxy = None
                if classified is not None or lsb_class is not None or morphology is not None or valid_redshift is not None:
                    # Check if this galaxy meets our classified criteria
                    classified_galaxy = session.query(Classification).filter_by(
                        user_id=user_id, galaxy_id=current_galaxy.id
                    ).first()
                    
                    if classified is not None:
                        if (classified and not classified_galaxy) or (not classified and classified_galaxy):
                            continue  # Skip this galaxy if it doesn't match classified criteria
                    
                    # Check lsb_class criteria if specified
                    if lsb_class is not None and isinstance(lsb_class, int):
                        if not classified_galaxy or classified_galaxy.lsb_class != lsb_class:
                            continue  # Skip if not classified or lsb_class doesn't match
                    
                    # Check morphology criteria if specified
                    if morphology is not None and isinstance(morphology, int):
                        if not classified_galaxy or classified_galaxy.morphology != morphology:
                            continue  # Skip if not classified or morphology doesn't match
                
                if with_redshift is not None:
                    # Check redshift criteria if specified
                    if with_redshift is True and (current_galaxy.redshift_x is None or current_galaxy.redshift_y is None):
                        continue  # Skip galaxies without redshift data
                    elif with_redshift is False and (current_galaxy.redshift_x is not None or current_galaxy.redshift_y is not None):
                        continue  # Skip galaxies with redshift data

                # Always require redshift data if valid_redshift is specified
                if valid_redshift is not None:
                    if (current_galaxy.redshift_x is None or current_galaxy.redshift_y is None):
                        continue  # Skip galaxies without redshift data when valid_redshift check is requested
                
                    # Check valid_redshift criteria if specified
                    classified_galaxy = session.query(Classification).filter_by(
                        user_id=user_id, galaxy_id=current_galaxy.id
                    ).first() if classified_galaxy is None else classified_galaxy
                    
                    # Skip if not classified or valid_redshift doesn't match
                    if not classified_galaxy or classified_galaxy.valid_redshift != valid_redshift:
                        continue
                
                # If we get here, the galaxy meets our criteria
                return current_galaxy
            
            # If we've exhausted all options, return None
            return None
        else:
            # No current_galaxy_id provided, select the first entry matching criteria
            query = session.query(cls)
            
            # Apply filters based on parameters
            classified_subq = session.query(Classification.galaxy_id).filter(Classification.user_id == user_id)
            
            # Filter by lsb_class if specified
            if lsb_class is not None and isinstance(lsb_class, int):
                lsb_subq = session.query(Classification.galaxy_id).filter(
                    Classification.user_id == user_id,
                    Classification.lsb_class == lsb_class
                )
                query = query.filter(cls.id.in_(lsb_subq))
                # Since we're requiring a specific classification, we also require the galaxy to be classified
                classified = True
            
            # Filter by morphology if specified
            if morphology is not None and isinstance(morphology, int):
                morph_subq = session.query(Classification.galaxy_id).filter(
                    Classification.user_id == user_id,
                    Classification.morphology == morphology
                )
                query = query.filter(cls.id.in_(morph_subq))
                # Since we're requiring a specific classification, we also require the galaxy to be classified
                classified = True
            
            if classified:
                query = query.filter(cls.id.in_(classified_subq))
            else:
                query = query.filter(~cls.id.in_(classified_subq))
            
            skipped_subq = session.query(SkippedGalaxy.galaxy_id).filter(SkippedGalaxy.user_id == user_id)
            if skipped:
                query = query.filter(cls.id.in_(skipped_subq))
            else:
                query = query.filter(~cls.id.in_(skipped_subq))
            
            # Apply redshift filter if specified
            if with_redshift is True:
                query = query.filter(cls.redshift_x.isnot(None), cls.redshift_y.isnot(None))
            elif with_redshift is False:
                query = query.filter(cls.redshift_x.is_(None), cls.redshift_y.is_(None))
            
            # Apply valid_redshift filter if specified
            if valid_redshift is not None:
                valid_redshift_subq = session.query(Classification.galaxy_id).filter(
                    Classification.user_id == user_id,
                    Classification.valid_redshift == valid_redshift
                )
                query = query.filter(cls.id.in_(valid_redshift_subq))
            
            # Sort results for consistency:
            # 1. Prioritize galaxies that have no previous galaxy (start of chains)
            # 2. Then sort by galaxy ID for consistent ordering
            query = query.order_by(cls.previous_id.is_(None).desc(), cls.id)
            
            # Return the first matching galaxy
            return query.first()
    
    @classmethod
    def get_previous_for_user(cls, session, user_id, current_galaxy_id, skipped=False, classified=None, 
                             with_redshift=None, valid_redshift=None, lsb_class=None, morphology=None):
        """Get previous galaxy using the previous_id field, filtering by skipped and classified status"""
        # Start from the galaxy specified by current_galaxy_id
        current_galaxy = session.query(cls).filter_by(id=current_galaxy_id).first()
        
        if not current_galaxy:
            return None  # Specified galaxy not found
        
        # Set to track visited galaxies to avoid cycles
        visited_ids = set([current_galaxy.id])
        
        # Hop backward through the galaxy chain
        while current_galaxy and current_galaxy.previous and current_galaxy.previous.id not in visited_ids:
            current_galaxy = current_galaxy.previous
            
            if not current_galaxy:
                break
                
            visited_ids.add(current_galaxy.id)
            
            if skipped is not None:
                # Check if this galaxy meets our skipped criteria
                skipped_galaxy = session.query(SkippedGalaxy).filter_by(
                    user_id=user_id, galaxy_id=current_galaxy.id
                ).first()
                
                if (skipped and not skipped_galaxy) or (not skipped and skipped_galaxy):
                    continue  # Skip this galaxy if it doesn't match skipped criteria
            
            classified_galaxy = None
            if classified is not None or lsb_class is not None or morphology is not None or valid_redshift is not None:
                # Check if this galaxy meets our classified criteria
                classified_galaxy = session.query(Classification).filter_by(
                    user_id=user_id, galaxy_id=current_galaxy.id
                ).first()
                
                if classified is not None:
                    if (classified and not classified_galaxy) or (not classified and classified_galaxy):
                        continue  # Skip this galaxy if it doesn't match classified criteria
                
                # Check lsb_class criteria if specified
                if lsb_class is not None and isinstance(lsb_class, int):
                    if not classified_galaxy or classified_galaxy.lsb_class != lsb_class:
                        continue  # Skip if not classified or lsb_class doesn't match
                
                # Check morphology criteria if specified
                if morphology is not None and isinstance(morphology, int):
                    if not classified_galaxy or classified_galaxy.morphology != morphology:
                        continue  # Skip if not classified or morphology doesn't match
            
            if with_redshift is not None:
                # Check redshift criteria if specified
                if with_redshift is True and (current_galaxy.redshift_x is None or current_galaxy.redshift_y is None):
                    continue  # Skip galaxies without redshift data
                elif with_redshift is False and (current_galaxy.redshift_x is not None or current_galaxy.redshift_y is not None):
                    continue  # Skip galaxies with redshift data
            
            # Always require redshift data if valid_redshift is specified
            if valid_redshift is not None:
                if (current_galaxy.redshift_x is None or current_galaxy.redshift_y is None):
                    continue  # Skip galaxies without redshift data when valid_redshift check is requested
            
                # Check valid_redshift criteria if specified
                classified_galaxy = session.query(Classification).filter_by(
                    user_id=user_id, galaxy_id=current_galaxy.id
                ).first() if classified_galaxy is None else classified_galaxy
                
                # Skip if not classified or valid_redshift doesn't match
                if not classified_galaxy or classified_galaxy.valid_redshift != valid_redshift:
                    continue
            
            # If we get here, the galaxy meets our criteria
            return current_galaxy
        
        # If we've exhausted all options, return None
        return None

    @classmethod
    def get_by_id(cls, session, galaxy_id):
        """Get galaxy by ID"""
        return session.query(cls).filter(cls.id == galaxy_id).first()


class SkippedGalaxy(Base):
    # list of galaxies that are skiped for the suer
    __tablename__ = 'skipped_galaxies'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    galaxy_id = Column(String, ForeignKey('galaxies.id'), nullable=False)
    date_skipped = Column(DateTime, default=datetime.now)
    comments = Column(String)
    # Relationships
    user = relationship("User", back_populates="skipped_galaxies")
    galaxy = relationship("Galaxy", back_populates="skipped_galaxies")
    
    @classmethod
    def create(cls, session, user_id, galaxy_id, comments):
        """Create a new skipped galaxy entry"""
        new_skipped_galaxy = SkippedGalaxy(
            user_id=user_id,
            galaxy_id=galaxy_id,
            comments=comments,
            date_skipped=datetime.now()
        )
        session.add(new_skipped_galaxy)
        session.flush()  # To get the ID without committing
        return new_skipped_galaxy
    
    @classmethod
    def get_skipped(cls, session, user_id):
        """Get all skipped galaxies for a user"""
        return session.query(cls).filter(cls.user_id == user_id).all()
    
    @classmethod
    def get_skipped_count(cls, session, user_id):
        """Get count of skipped galaxies for a user"""
        return session.query(cls).filter(cls.user_id == user_id).count()
    
    @classmethod
    def delete_skipped(cls, session, user_id, galaxy_id):
        """Delete a skipped galaxy entry"""
        skipped_galaxy = session.query(cls).filter_by(user_id=user_id, galaxy_id=galaxy_id).first()
        if skipped_galaxy:
            session.delete(skipped_galaxy)
            return True
        return False
    
    @classmethod
    def create_or_update(cls, session, user_id, galaxy_id, comments):
        """Create or update a skipped galaxy entry"""
        # Check if a skipped galaxy already exists for this user and galaxy
        existing_skipped = session.query(cls).filter_by(
            user_id=user_id, galaxy_id=galaxy_id
        ).first()

        if existing_skipped:
            # Update the existing skipped galaxy
            existing_skipped.comments = comments
            existing_skipped.date_skipped = datetime.now()
            return existing_skipped
        else:
            # Create a new skipped galaxy
            new_skipped_galaxy = cls(
                user_id=user_id,
                galaxy_id=galaxy_id,
                comments=comments,
                date_skipped=datetime.now()
            )
            session.add(new_skipped_galaxy)
            session.flush()
            return new_skipped_galaxy
    



class Classification(Base):
    __tablename__ = 'classifications'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    galaxy_id = Column(String, ForeignKey('galaxies.id'), nullable=False)
    lsb_class = Column(Integer, nullable=False)  # -1, 0, 1
    morphology = Column(Integer, nullable=False)  # -1, 0, 1, 2 
    comments = Column(String)
    sky_bkg = Column(String)  # 'masked' or 'un_masked'
    date_classified = Column(DateTime, default=datetime.now)
    awesome_flag = Column(Boolean, default=False)
    valid_redshift = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="classifications")
    galaxy = relationship("Galaxy", back_populates="classifications")
    
    @classmethod
    def create(cls, session, user_id, galaxy_id, lsb_class, morphology, comments, awesome_flag, valid_redshift):
        """Create a new classification entry"""
        new_classification = Classification(
            user_id=user_id,
            galaxy_id=galaxy_id,
            lsb_class=lsb_class,
            morphology=morphology,
            comments=comments,
            awesome_flag=awesome_flag,
            valid_redshift=valid_redshift,
            date_classified=datetime.now(),
            sky_bkg = 'masked' # Or determine based on logic
        )
        session.add(new_classification)
    
    @classmethod
    def update(cls, session, classification_id, lsb_class, morphology, comments, awesome_flag, valid_redshift):
        """Update an existing classification entry"""
        classification = session.query(cls).filter(cls.id == classification_id).first()
        if classification:
            classification.lsb_class = lsb_class
            classification.morphology = morphology
            classification.comments = comments
            classification.awesome_flag = awesome_flag
            classification.valid_redshift = valid_redshift
            classification.date_classified = datetime.now()
            return True
        return False

    @classmethod
    def create_or_update(cls, session, user_id, galaxy_id, lsb_class, morphology, comments, awesome_flag, valid_redshift):
        """Create or update a classification entry"""
        # Check if a classification already exists for this user and galaxy
        existing_classification = session.query(cls).filter_by(
            user_id=user_id, galaxy_id=galaxy_id
        ).first()

        if existing_classification:
            # Update the existing classification
            existing_classification.lsb_class = lsb_class
            existing_classification.morphology = morphology
            existing_classification.comments = comments
            existing_classification.awesome_flag = awesome_flag
            existing_classification.valid_redshift = valid_redshift
            existing_classification.date_classified = datetime.now()
            return existing_classification
        else:
            # Create a new classification
            new_classification = cls(
                user_id=user_id,
                galaxy_id=galaxy_id,
                lsb_class=lsb_class,
                morphology=morphology,
                comments=comments,
                awesome_flag=awesome_flag,
                valid_redshift=valid_redshift,
                date_classified=datetime.now(),
                sky_bkg='masked'  # Or determine based on logic
            )
            session.add(new_classification)
            session.flush()  # To get the ID without committing
            return new_classification

    @classmethod
    def get_or_create(cls, session, user_id, galaxy_id, lsb_class=None, morphology=None, 
                     comments=None, awesome_flag=False, valid_redshift=False):
        """Get or create a classification entry"""
        
        # Check if a classification already exists for this user and galaxy
        existing_classification = session.query(cls).filter_by(
            user_id=user_id, galaxy_id=galaxy_id
        ).first()

        if existing_classification:
            # If no new classification data provided, just return existing
            if lsb_class is None:
                return existing_classification
                
            # Otherwise update the existing classification
            existing_classification.lsb_class = lsb_class
            existing_classification.morphology = morphology
            existing_classification.comments = comments
            existing_classification.awesome_flag = awesome_flag
            existing_classification.valid_redshift = valid_redshift
            existing_classification.date_classified = datetime.now()
            return existing_classification
        else:
            # Only create if classification data is provided
            if lsb_class is not None:
                new_classification = cls(
                    user_id=user_id,
                    galaxy_id=galaxy_id,
                    lsb_class=lsb_class,
                    morphology=morphology,
                    comments=comments,
                    awesome_flag=awesome_flag,
                    valid_redshift=valid_redshift,
                    date_classified=datetime.now(),
                    sky_bkg='masked'  # Or determine based on logic
                )
                session.add(new_classification)
                session.flush()  # To get the ID without committing
                return new_classification
            return None

    @classmethod
    def get_progress(cls, session, user_id):
        """Get classification progress for a user"""
        # Return dict with classified count, total, and percentage
        total = session.query(Galaxy).count()
        classified_count = session.query(Classification).filter_by(user_id=user_id).count()
        percentage = (classified_count / total) * 100 if total > 0 else 0
        return {
            'classified_count': classified_count,
            'total': total,
            'percentage': percentage
        }
    
    @classmethod
    def get_stats_for_user(cls, session, user_id):
        """Get classification statistics for a user"""
        # Implementation would query database and prapare all stats used in results.html
        # Get classification stats
        total_classified = session.query(Classification).filter_by(user_id=user_id).count()
        lsb_count = session.query(Classification).filter_by(user_id=user_id, lsb_class=1).count()
        awesome_count = session.query(Classification).filter_by(user_id=user_id, awesome_flag=True).count()

        lsb_counts = {
            'failed': session.query(Classification).filter_by(user_id=user_id, lsb_class=-1).count(),
            'non_lsb': session.query(Classification).filter_by(user_id=user_id, lsb_class=0).count(),
            'lsb': lsb_count
        }

        morph_counts = {
            'featureless': session.query(Classification).filter_by(user_id=user_id, morphology=-1).count(),
            'not_sure': session.query(Classification).filter_by(user_id=user_id, morphology=0).count(),
            'ltg': session.query(Classification).filter_by(user_id=user_id, morphology=1).count(),
            'etg': session.query(Classification).filter_by(user_id=user_id, morphology=2).count(),
        }

        # Get recent classifications
        recent_classifications = session.query(Classification).filter_by(user_id=user_id).order_by(Classification.date_classified.desc()).limit(10).all()

        stats = {
            'total_classified': total_classified,
            'lsb_count': lsb_count,
            'awesome_count': awesome_count,
            'lsb_counts': lsb_counts,
            'morph_counts': morph_counts,
            'recent_classifications': recent_classifications
        }
        return stats




