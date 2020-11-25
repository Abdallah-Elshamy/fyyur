#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from datetime import datetime
from pytz import UTC
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
import sys
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

# Use association object to hold the extra start_time data instead of
# association table to implement Many to Many relation
class Show(db.Model):
    __tablename__ = 'Show'

    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'),
        primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'),
        primary_key=True)
    start_time = db.Column(db.String(30), primary_key=True)
    artist = db.relationship("Artist", backref=db.backref('shows', lazy=True))

    def __repr__(self):
        return f"Artist {self.artist_id} performs on Venue {self.venue_id}"

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(2), nullable=False)
    address = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(12))
    genres = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    shows = db.relationship('Show', cascade="all, delete, delete-orphan")

    def __repr__(self):
        return f"Venue {self.id}: {self.name}"


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(2), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(12))
    genres = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))

    def __repr__(self):
        return f"Artist {self.id}: {self.name}"

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Helper fuctions.
#----------------------------------------------------------------------------#

def search(type, search_term):
  '''
  a general implementation for the search functionality that takes
  a "type" (in our case: Artist or Venue), search for the "search_term"
  in the names of the objects of "type" and return the results.
  '''
  search_term = "%" + search_term + "%"
  search_candidates = type.query.filter(type.name.ilike(search_term)).all()
  data = []
  for candidate in search_candidates:
    data.append({
      "id": candidate.id,
      "name": candidate.name
    })
  return {
    "count": len(search_candidates),
    "data": data
  }

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # get all distinct areas (city + state)
  areas = Venue.query.with_entities(Venue.city, Venue.state).distinct().all()
  data = []
  # Group venues  that in the same area and show their links.
  for area in areas:
    venues = Venue.query.with_entities(Venue.id, Venue.name).\
             filter_by(city=area[0],state=area[1]).all()
    venues_data = []
    for venue in venues:
      venues_data.append({
        "id": venue[0],
        "name": venue[1]
      })
    data.append({
      "city": area[0],
      "state": area[1],
      "venues": venues_data
    })

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  search_term = request.form.get('search_term', '')
  return render_template('pages/search_venues.html', results=search(Venue, search_term),
                         search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  venue = Venue.query.get(venue_id)
  # Venue with venue_id is not found
  if venue == None:
    abort (404)
  # join the tables and retrieve the data that you will need
  shows_data = Artist.query.join(Show).join(Venue).filter(Venue.id==venue_id).\
        with_entities(Artist.id,Artist.name, Artist.image_link, Show.start_time).all()
  past_shows_list = []
  upcoming_shows_list = []
  past_shows_count = 0
  upcoming_shows_count = 0
  for data in shows_data:
    formatted_data = {
      "artist_id": data[0],
      "artist_name": data[1],
      "artist_image_link": data[2],
      "start_time": data[3]
    }
    # determine if it is past or upcoming show
    if datetime.now() > dateutil.parser.parse(data[3], ignoretz=True):
      past_shows_list.append(formatted_data)
      past_shows_count += 1
    else:
      upcoming_shows_list.append(formatted_data)
      upcoming_shows_count += 1

  # Format the data that will be sent to the template
  data={
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres.split(','),
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": past_shows_list,
    "upcoming_shows": upcoming_shows_list,
    "past_shows_count": past_shows_count,
    "upcoming_shows_count": upcoming_shows_count
  }
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  form = VenueForm(request.form)
  if form.validate_on_submit():
    try:
      # Create Venue using form data
      venue = Venue(name=form.name.data, city=form.city.data,
                    state=form.state.data, address=form.address.data,
                    image_link=form.image_link.data, website=form.website.data,
                    phone=form.phone.data, genres=','.join(form.genres.data),
                    seeking_talent=form.seeking_talent.data,
                    seeking_description=form.seeking_description.data,
                    facebook_link=form.facebook_link.data)
      db.session.add(venue)
      db.session.commit()
      # on successful db insert, flash success
      flash('Venue ' + form.name.data + ' was successfully listed!')
    except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Venue ' + form.name.data + ' could not be listed.', 'error')
      print(sys.exc_info())
    finally:
      db.session.close()

    return render_template('pages/home.html')

  return render_template('forms/new_venue.html', form=form)


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    venue = Venue.query.get(venue_id)
    # Venue with venue_id is not found
    if venue == None:
      abort (404)
    venue_name = venue.name
    db.session.delete(venue)
    db.session.commit()
    # on successful db delete, flash success
    flash('Venue ' + venue_name + ' was successfully deleted!')
  except:
    db.session.rollback()
    # on unsuccessful db delete, flash an error instead.
    flash('An error occurred. Venue could not be deleted.', 'error')
    print(sys.exc_info())
  finally:
    db.session.close()

  return redirect(url_for('venues'))

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  artists = Artist.query.all()
  formatted_data = []
  for artist in artists:
    formatted_data.append({
        "id": artist.id,
        "name": artist.name
        })

  return render_template('pages/artists.html', artists=formatted_data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  search_term = request.form.get('search_term', '')
  return render_template('pages/search_artists.html', results=search(Artist, search_term),
                         search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  artist = Artist.query.get(artist_id)
  # Artist with artist_id is not found
  if artist == None:
    abort (404)

  # join the tables and retrieve the data that you will need
  shows_data = Venue.query.join(Show).join(Artist).filter(Artist.id==artist_id).\
        with_entities(Venue.id,Venue.name, Venue.image_link, Show.start_time).all()
  past_shows_list = []
  past_shows_count = 0
  upcoming_shows_list = []
  upcoming_shows_count = 0
  for data in shows_data:
    formatted_data = {
      "venue_id": data[0],
      "venue_name": data[1],
      "venue_image_link": data[2],
      "start_time": data[3]
    }
    # determine if it is past or upcoming show
    if datetime.now() > dateutil.parser.parse(data[3], ignoretz=True):
      past_shows_list.append(formatted_data)
      past_shows_count += 1
    else:
      upcoming_shows_list.append(formatted_data)
      upcoming_shows_count += 1

  # Format the data that will be sent to the template
  data={
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres.split(','),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": past_shows_list,
    "upcoming_shows": upcoming_shows_list,
    "past_shows_count": past_shows_count,
    "upcoming_shows_count": upcoming_shows_count
  }

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  artist = Artist.query.get(artist_id)
  # Artist with artist_id is not found
  if artist == None:
    abort (404)
  form = ArtistForm()
  # Populate the form with the data of the object we want to edit
  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.image_link.data = artist.image_link
  form.website.data = artist.website
  form.phone.data = artist.phone
  form.genres.data = artist.genres.split(',')
  form.facebook_link.data = artist.facebook_link
  form.seeking_venue.data = artist.seeking_venue
  form.seeking_description.data = artist.seeking_description

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  form = ArtistForm(request.form)
  artist = Artist.query.get(artist_id)
  # Artist with artist_id is not found
  if artist == None:
    abort (404)
  if form.validate_on_submit():
    try:
      artist.name = form.name.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.image_link = form.image_link.data
      artist.website = form.website.data
      artist.phone = form.phone.data
      artist.genres = ','.join(form.genres.data)
      artist.facebook_link = form.facebook_link.data
      artist.seeking_venue = form.seeking_venue.data
      artist.seeking_description = form.seeking_description.data

      db.session.commit()
      # on successful db insert, flash success
      flash('Artist ' + form.name.data + ' was successfully edited!')
    except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Artist ' + form.name.data + ' could not be edited.', 'error')
      print(sys.exc_info())
    finally:
      db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.get(venue_id)
  # Venue with venue_id is not found
  if venue == None:
    abort (404)
  form = VenueForm()
  # Populate the form with the data of the object we want to edit
  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.image_link.data = venue.image_link
  form.website.data = venue.website
  form.phone.data = venue.phone
  form.genres.data = venue.genres.split(',')
  form.facebook_link.data = venue.facebook_link
  form.seeking_talent.data = venue.seeking_talent
  form.seeking_description.data = venue.seeking_description

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm(request.form)
  venue = Venue.query.get(venue_id)
  # Venue with venue_id is not found
  if venue == None:
    abort (404)
  if form.validate_on_submit():
    try:
      venue.name = form.name.data
      venue.city = form.city.data
      venue.state = form.state.data
      venue.address = form.address.data
      venue.image_link = form.image_link.data
      venue.website = form.website.data
      venue.phone = form.phone.data
      venue.genres = ','.join(form.genres.data)
      venue.facebook_link = form.facebook_link.data
      venue.seeking_talent = form.seeking_talent.data
      venue.seeking_description = form.seeking_description.data

      db.session.commit()
      # on successful db insert, flash success
      flash('Venue ' + form.name.data + ' was successfully edited!')
    except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Venue ' + form.name.data + ' could not be edited.', 'error')
      print(sys.exc_info())
    finally:
      db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))
  return render_template('forms/edit_venue.html', form=form, venue=venue)

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  form = ArtistForm(request.form)
  if form.validate_on_submit():
    try:
      # Create Artist using form data
      artist = Artist(name=form.name.data, city=form.city.data,
                      state=form.state.data, facebook_link=form.facebook_link.data,
                      image_link=form.image_link.data, website=form.website.data,
                      phone=form.phone.data, genres=','.join(form.genres.data),
                      seeking_venue=form.seeking_venue.data,
                      seeking_description=form.seeking_description.data)
      db.session.add(artist)
      db.session.commit()
      # on successful db insert, flash success
      flash('Artist ' + form.name.data + ' was successfully listed!')
    except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Artist ' + form.name.data + ' could not be listed.', 'error')
      print(sys.exc_info())
    finally:
      db.session.close()

    return render_template('pages/home.html')

  return render_template('forms/new_artist.html', form=form)

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  shows = Show.query.all()
  formatted_data = []
  for show in shows:
    formatted_data.append({
      "venue_id": show.venue_id,
      "venue_name": Venue.query.get(show.venue_id).name,
      "artist_id": show.artist_id,
      "artist_name": Artist.query.get(show.artist_id).name,
      "artist_image_link": Artist.query.get(show.artist_id).image_link,
      "start_time": show.start_time
    })

  return render_template('pages/shows.html', shows=formatted_data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  form = ShowForm(request.form)
  if form.validate_on_submit():
    try:
      # Create Show using form data
      show = Show(artist_id=form.artist_id.data,
                  venue_id=form.venue_id.data,
                  start_time=form.start_time.data)
      db.session.add(show)
      db.session.commit()
      # on successful db insert, flash success
      flash('Show was successfully listed!')
    except:
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Show could not be listed.', 'error')
      print(sys.exc_info())
    finally:
      db.session.close()

    return render_template('pages/home.html')

  return render_template('forms/new_show.html', form=form)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
