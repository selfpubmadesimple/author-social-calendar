import os
import io
import logging
from datetime import date as d
from flask import Flask, render_template, request, send_file, flash, redirect, url_for, session, jsonify
from markupsafe import escape
import pandas as pd
import zipfile
import requests
from urllib.parse import urlparse
from werkzeug.utils import secure_filename

from ai import generate_posts
from utils import build_date_series, posts_to_dataframe
from sheets import write_dataframe
from models import db, BookForm, GeneratedCalendar, Campaign, ScheduledPost
import json
from holidays import get_holidays_for_month, format_holidays_for_ai
from image_generator import image_generator

# Security: Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_images(max_age_hours=24):
    """Delete images older than max_age_hours from static/images directory."""
    from datetime import datetime, timedelta
    
    images_dir = os.path.join('static', 'images')
    if not os.path.exists(images_dir):
        return
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    deleted_count = 0
    
    try:
        for filename in os.listdir(images_dir):
            filepath = os.path.join(images_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(filepath):
                continue
            
            # Get file modification time
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            # Delete if older than cutoff
            if file_time < cutoff_time:
                os.remove(filepath)
                deleted_count += 1
                logging.debug(f"Deleted old image: {filename}")
        
        if deleted_count > 0:
            logging.info(f"Cleanup: Deleted {deleted_count} old image(s)")
    except Exception as e:
        logging.error(f"Error during image cleanup: {str(e)}")

# Configure logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

app = Flask(__name__)
# Security: Require SESSION_SECRET to be set - no fallback
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise RuntimeError("SESSION_SECRET environment variable must be set for security")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Run cleanup on startup to remove old images
cleanup_old_images()

@app.route("/")
def form():
    """Display the main form for collecting book and campaign details."""
    # Get the most complete form submission (with substantial data) to pre-populate
    # Skip test entries that only have basic fields filled
    recent_form = BookForm.query.filter(
        BookForm.goal.isnot(None),
        BookForm.goal != '',
        BookForm.differentiator.isnot(None),
        BookForm.differentiator != ''
    ).order_by(BookForm.created_at.desc()).first()
    
    # Fallback to any recent form if no complete ones exist
    if not recent_form:
        recent_form = BookForm.query.order_by(BookForm.created_at.desc()).first()
    
    return render_template("form.html", recent_form=recent_form)

@app.route("/generate", methods=["POST"])
def generate():
    """Generate social media posts based on form input and display preview."""
    try:
        # Validate required fields
        required_fields = ['book_title', 'start_date']
        form_data = request.form.to_dict()
        missing_fields = [field for field in required_fields if not form_data.get(field)]
        
        if missing_fields:
            app.logger.error(f"Missing required fields: {missing_fields}")
            # Security: Escape field names to prevent XSS
            escaped_fields = ', '.join(escape(field) for field in missing_fields)
            return f"""
            <div class="container mt-4">
                <div class="alert alert-danger">
                    <h4><i class="fas fa-exclamation-triangle me-2"></i>Missing Information</h4>
                    <p>Please fill in all required fields: {escaped_fields}</p>
                    <a href="/" class="btn btn-primary">Go Back</a>
                </div>
            </div>
            """, 400
        
        app.logger.info(f"Processing form data: {list(form_data.keys())}")
        app.logger.debug(f"Form values: book_title='{form_data.get('book_title')}', start_date='{form_data.get('start_date')}'")
        
        # Handle file uploads
        upload_dir = os.path.join(app.static_folder, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        brand_assets = {
            'book_cover_path': None,
            'author_photo_path': None,
            'primary_color': form_data.get('primary_color', '#FF6B6B'),
            'secondary_color': form_data.get('secondary_color', '#4ECDC4'),
            'background_color': form_data.get('background_color', '#F7F7F7'),
            'heading_font': form_data.get('heading_font', 'Playfair Display'),
            'body_font': form_data.get('body_font', 'Open Sans')
        }
        
        # Save uploaded book cover with security validation
        if 'book_cover' in request.files:
            book_cover = request.files['book_cover']
            if book_cover and book_cover.filename:
                if not allowed_file(book_cover.filename):
                    app.logger.warning(f"Rejected book cover: invalid file type '{book_cover.filename}'")
                else:
                    # Read file into memory to validate
                    file_data = book_cover.read()
                    
                    # Security: Check file size
                    if len(file_data) > MAX_FILE_SIZE:
                        app.logger.warning(f"Rejected book cover: file too large ({len(file_data)} bytes)")
                    else:
                        # Security: Validate it's a real image using PIL
                        try:
                            from PIL import Image
                            img = Image.open(io.BytesIO(file_data))
                            img.verify()  # Verify it's a valid image
                            
                            # Save the validated file
                            ext = book_cover.filename.rsplit('.', 1)[1].lower()
                            filename = f"book_cover_{os.urandom(8).hex()}.{ext}"
                            filepath = os.path.join(upload_dir, filename)
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                            brand_assets['book_cover_path'] = filepath
                            app.logger.info(f"Saved book cover: {filename}")
                        except Exception as e:
                            app.logger.warning(f"Rejected book cover: not a valid image - {str(e)}")
        
        # Save uploaded author photo with security validation
        if 'author_photo' in request.files:
            author_photo = request.files['author_photo']
            if author_photo and author_photo.filename:
                if not allowed_file(author_photo.filename):
                    app.logger.warning(f"Rejected author photo: invalid file type '{author_photo.filename}'")
                else:
                    # Read file into memory to validate
                    file_data = author_photo.read()
                    
                    # Security: Check file size
                    if len(file_data) > MAX_FILE_SIZE:
                        app.logger.warning(f"Rejected author photo: file too large ({len(file_data)} bytes)")
                    else:
                        # Security: Validate it's a real image using PIL
                        try:
                            from PIL import Image
                            img = Image.open(io.BytesIO(file_data))
                            img.verify()  # Verify it's a valid image
                            
                            # Save the validated file
                            ext = author_photo.filename.rsplit('.', 1)[1].lower()
                            filename = f"author_photo_{os.urandom(8).hex()}.{ext}"
                            filepath = os.path.join(upload_dir, filename)
                            with open(filepath, 'wb') as f:
                                f.write(file_data)
                            brand_assets['author_photo_path'] = filepath
                            app.logger.info(f"Saved author photo: {filename}")
                        except Exception as e:
                            app.logger.warning(f"Rejected author photo: not a valid image - {str(e)}")
        
        app.logger.info(f"Brand assets: {brand_assets}")
        
        # Validate and parse start_date
        start_date_str = form_data.get("start_date") or d.today().isoformat()
        try:
            start_date = d.fromisoformat(start_date_str)
            app.logger.debug(f"Parsed start_date: {start_date}")
        except ValueError as date_error:
            app.logger.error(f"Invalid date format: {start_date_str} - {str(date_error)}")
            return f"""
            <div class="container mt-4">
                <div class="alert alert-danger">
                    <h4><i class="fas fa-calendar-times me-2"></i>Invalid Date</h4>
                    <p>Please enter a valid start date in YYYY-MM-DD format.</p>
                    <p>Received: {start_date_str}</p>
                    <a href="/" class="btn btn-primary">Go Back</a>
                </div>
            </div>
            """, 400
        
        # Save form data to database with error handling
        try:
            book_form = BookForm()
            book_form.book_title = form_data.get("book_title", "")
            book_form.age_range = form_data.get("age_range", "ages 4–8")
            book_form.audience = form_data.get("audience", "families, educators, authors")
            book_form.tone = form_data.get("tone", "Warm")
            book_form.goal = form_data.get("goal", "")
            book_form.themes = form_data.get("themes", "courage, kindness, friendship")
            book_form.differentiator = form_data.get("differentiator", "")
            book_form.events = form_data.get("events", "")
            book_form.additional_context = form_data.get("additional_context", "")
            book_form.start_date = start_date_str
            book_form.cadence = form_data.get("cadence", "daily")
            book_form.primary_color = form_data.get("primary_color", "#FF6B6B")
            book_form.secondary_color = form_data.get("secondary_color", "#4ECDC4")
            book_form.background_color = form_data.get("background_color", "#F7F7F7")
            book_form.heading_font = form_data.get("heading_font", "Playfair Display")
            book_form.body_font = form_data.get("body_font", "Open Sans")
            db.session.add(book_form)
            db.session.commit()
            app.logger.info(f"Successfully saved form data to database with ID: {book_form.id}")
        except Exception as db_error:
            app.logger.error(f"Database error saving form: {str(db_error)}")
            db.session.rollback()
            # Continue without saving - generation can still work
            book_form = None
        
        # Collect form data for AI generation
        data = {
            "book_title": form_data.get("book_title", ""),
            "audience": form_data.get("audience", "families, educators, authors"),
            "goal": form_data.get("goal", ""),
            "tone": form_data.get("tone", "Warm"),
            "events": form_data.get("events", ""),
            "themes": form_data.get("themes", "courage, kindness, friendship"),
            "age_range": form_data.get("age_range", "ages 4–8"),
            "differentiator": form_data.get("differentiator", ""),
            "additional_context": form_data.get("additional_context", ""),
        }
        
        cadence = form_data.get("cadence", "daily")

        # Get holidays for the date range with error handling
        try:
            holidays = get_holidays_for_month(start_date, num_days=30)
            app.logger.debug(f"Found {len(holidays)} holidays for date range starting {start_date}")
        except Exception as holiday_error:
            app.logger.warning(f"Error getting holidays, proceeding without them: {str(holiday_error)}")
            holidays = []
        
        # Check if test mode is enabled (skip AI generation for faster testing)
        test_mode = form_data.get("test_mode") == "on"
        
        if test_mode:
            app.logger.info(f"🚀 TEST MODE: Using sample posts for quick testing (book: '{data['book_title']}')")
            from fallback_posts import generate_fallback_posts
            posts = generate_fallback_posts(data, num_days=30, holidays=holidays)
            app.logger.info(f"✓ Generated {len(posts)} sample posts instantly")
            
            # Generate 5 sample images with brand colors for testing (much faster than 30)
            app.logger.info("🎨 Generating 5 sample images with your brand colors for testing...")
            from image_generator import image_generator
            images_generated = 0
            for i in range(min(5, len(posts))):
                try:
                    result = image_generator.create_social_media_image(
                        image_idea=posts[i]['image_idea'],
                        book_title=data['book_title'],
                        post_theme=posts[i]['theme'],
                        hook=posts[i]['hook'],
                        brand_assets=brand_assets
                    )
                    if result and result.get('success'):
                        posts[i]['image_url'] = result.get('image_url', '')
                        posts[i]['image_path'] = result.get('image_path', '')
                        images_generated += 1
                        app.logger.info(f"✓ Sample image {i+1}/5 generated")
                except Exception as img_error:
                    app.logger.warning(f"Could not generate sample image {i+1}: {str(img_error)}")
            
            app.logger.info(f"✓ Test mode complete: {len(posts)} posts, {images_generated} sample images")
        else:
            # Generate posts using AI with detailed logging
            app.logger.info(f"Starting AI generation for book: '{data['book_title']}'")
            app.logger.debug(f"AI generation parameters: {len(holidays)} holidays, cadence={cadence}")
            
            try:
                posts = generate_posts(data, num_days=30, holidays=holidays)
                app.logger.info(f"Successfully generated {len(posts) if posts else 0} posts")
            except Exception as ai_error:
                app.logger.error(f"AI generation failed: {str(ai_error)}")
                # Re-raise to be caught by outer exception handler
                raise ai_error
        
        # Build date series and create DataFrame with error handling
        try:
            dates = build_date_series(start_date, 30, cadence=cadence)
            app.logger.debug(f"Generated {len(dates)} dates with cadence '{cadence}'")
            
            df = posts_to_dataframe(posts, dates)
            app.logger.debug(f"Created DataFrame with {len(df)} rows")
        except Exception as data_error:
            app.logger.error(f"Error processing generated data: {str(data_error)}")
            raise data_error

        # Store brand assets and posts in database (not session - avoids cookie size limit)
        calendar_session_id = os.urandom(16).hex()  # Unique ID for this calendar
        
        try:
            calendar = GeneratedCalendar()
            calendar.session_id = calendar_session_id
            calendar.book_title = data['book_title']
            calendar.posts_json = json.dumps(posts)
            calendar.brand_assets_json = json.dumps(brand_assets)
            db.session.add(calendar)
            db.session.commit()
            app.logger.info(f"Stored {len(posts)} posts in database with session ID: {calendar_session_id}")
        except Exception as db_error:
            app.logger.error(f"Failed to store calendar in database: {str(db_error)}")
            db.session.rollback()
        
        # Store only the session ID in cookie (tiny, no size limit issues)
        session['calendar_session_id'] = calendar_session_id
        session['brand_assets'] = brand_assets  # Keep for backward compatibility

        # Render preview with editable fields (text only, no images yet)
        app.logger.info("Successfully generated calendar, rendering preview")
        return render_template("preview.html", rows=df.to_dict(orient="records"))
        
    except Exception as e:
        app.logger.error(f"Error generating posts: {str(e)}")
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            return f"""
            <div class="container mt-4">
                <div class="alert alert-warning">
                    <h4><i class="fas fa-clock me-2"></i>Generation Timed Out</h4>
                    <p>The AI took longer than expected to generate your content. This sometimes happens during busy periods.</p>
                    <p><strong>Your form data has been saved!</strong> Please try again - it should work faster on the second attempt.</p>
                    <a href="/" class="btn btn-primary">Try Again</a>
                </div>
            </div>
            """, 500
        else:
            # Security: Escape error message to prevent XSS
            escaped_error = escape(error_msg)
            return f"""
            <div class="container mt-4">
                <div class="alert alert-danger">
                    <h4><i class="fas fa-exclamation-triangle me-2"></i>Generation Error</h4>
                    <p>Something went wrong while generating your content.</p>
                    <p><strong>Your form data has been saved!</strong> Please try again.</p>
                    <details class="mt-2">
                        <summary>Technical details</summary>
                        <code>{escaped_error}</code>
                    </details>
                    <a href="/" class="btn btn-primary mt-2">Try Again</a>
                </div>
            </div>
            """, 500

@app.route("/export-excel", methods=["POST"])
def export_excel():
    """Export the edited posts to Excel file."""
    try:
        rows = int(request.form["rows_count"])
        records = []
        
        for i in range(rows):
            records.append({
                "Date": request.form[f"date_{i}"],
                "Hook": request.form[f"hook_{i}"],
                "Caption": request.form[f"caption_{i}"],
                "Hashtags": request.form[f"hashtags_{i}"],
                "Image Idea": request.form[f"image_{i}"],
                "Image URL": request.form.get(f"image_url_{i}", ""),
                "Theme": request.form[f"theme_{i}"],
                "CTA": request.form[f"cta_{i}"]
            })
        
        df = pd.DataFrame(records)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name='Social Media Calendar', index=False)
            
            # Get the workbook and worksheet for formatting
            workbook = writer.book
            worksheet = writer.sheets['Social Media Calendar']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50 chars
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Style the header row
            from openpyxl.styles import Font, PatternFill
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="6A4BC4", end_color="6A4BC4", fill_type="solid")
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
        
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
        filename = f"social_media_calendar_{timestamp}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error exporting to Excel: {str(e)}")
        return f"<h3>Error exporting to Excel</h3><p>Error: {str(e)}</p>", 500

@app.route("/download-csv", methods=["POST"])
def download_csv():
    """Download the posts as a CSV file."""
    try:
        rows = int(request.form["rows_count"])
        records = []
        
        for i in range(rows):
            # Get image URL if available
            image_url = request.form.get(f"image_url_{i}", "")
            
            records.append({
                "Date": request.form[f"date_{i}"],
                "Hook": request.form[f"hook_{i}"],
                "Caption": request.form[f"caption_{i}"],
                "Hashtags": request.form[f"hashtags_{i}"],
                "Image Idea": request.form[f"image_{i}"],
                "Image URL": image_url,
                "Theme": request.form[f"theme_{i}"],
                "CTA": request.form[f"cta_{i}"]
            })
        
        df = pd.DataFrame(records)
        mem = io.BytesIO()
        mem.write(df.to_csv(index=False).encode("utf-8"))
        mem.seek(0)
        
        return send_file(
            mem, 
            mimetype="text/csv", 
            as_attachment=True, 
            download_name="social_calendar.csv"
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading CSV: {str(e)}")
        return f"<h3>Error creating CSV</h3><p>Please try again. Error: {str(e)}</p>", 500

@app.route("/download-canva", methods=["POST"])
def download_canva():
    """Download a Canva Bulk Create-formatted CSV file."""
    try:
        rows = int(request.form["rows_count"])
        records = []
        
        for i in range(rows):
            # Get image URL if available
            image_url = request.form.get(f"image_url_{i}", "")
            
            # Format for Canva Bulk Create with clear column names
            records.append({
                "Post_Date": request.form[f"date_{i}"],
                "Hook_Line": request.form[f"hook_{i}"],
                "Caption_Text": request.form[f"caption_{i}"],
                "Hashtags": request.form[f"hashtags_{i}"],
                "Image_Overlay_Text": request.form[f"hook_{i}"],  # Use hook as overlay text
                "Image_URL": image_url,
                "Post_Type": request.form[f"theme_{i}"].upper(),
                "CTA": request.form[f"cta_{i}"],
                "Image_Concept": request.form[f"image_{i}"]
            })
        
        df = pd.DataFrame(records)
        mem = io.BytesIO()
        mem.write(df.to_csv(index=False).encode("utf-8"))
        mem.seek(0)
        
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
        filename = f"canva_bulk_create_{timestamp}.csv"
        
        return send_file(
            mem, 
            mimetype="text/csv", 
            as_attachment=True, 
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error creating Canva CSV: {str(e)}")
        return f"<h3>Error creating Canva CSV</h3><p>Please try again. Error: {str(e)}</p>", 500

@app.route("/generate-image", methods=["POST"])
def generate_image():
    """Generate an AI image from an image idea description."""
    try:
        # Run cleanup before generating new images
        cleanup_old_images()
        
        data = request.get_json()
        if not data:
            return {"success": False, "error": "No JSON data provided"}, 400
            
        image_idea = data.get('image_idea', '').strip()
        book_title = data.get('book_title', 'children\'s book')
        post_theme = data.get('theme', 'social_media')
        hook = data.get('hook', '').strip()
        
        if not image_idea:
            return {"success": False, "error": "Image idea is required"}, 400
        
        app.logger.info(f"Generating image for idea: {image_idea}")
        if hook:
            app.logger.info(f"  Hook text: {hook}")
        
        # Get brand assets from session
        brand_assets = session.get('brand_assets', {})
        app.logger.info(f"🎨 Brand assets from session: {brand_assets}")
        
        # Log specific brand elements
        if brand_assets:
            if brand_assets.get('primary_color'):
                app.logger.info(f"  ✓ Primary color: {brand_assets.get('primary_color')}")
            if brand_assets.get('secondary_color'):
                app.logger.info(f"  ✓ Secondary color: {brand_assets.get('secondary_color')}")
            if brand_assets.get('background_color'):
                app.logger.info(f"  ✓ Background color: {brand_assets.get('background_color')}")
            if brand_assets.get('heading_font'):
                app.logger.info(f"  ✓ Heading font: {brand_assets.get('heading_font')}")
            if brand_assets.get('body_font'):
                app.logger.info(f"  ✓ Body font: {brand_assets.get('body_font')}")
            if brand_assets.get('book_cover_path'):
                app.logger.info(f"  ✓ Book cover: {brand_assets.get('book_cover_path')}")
            if brand_assets.get('author_photo_path'):
                app.logger.info(f"  ✓ Author photo: {brand_assets.get('author_photo_path')}")
        else:
            app.logger.warning("⚠️  No brand assets found in session!")
        
        # Generate the image with extended timeout handling
        result = image_generator.create_social_media_image(
            image_idea=image_idea,
            book_title=book_title,
            post_theme=post_theme,
            hook=hook,
            brand_assets=brand_assets
        )
        
        return result
        
    except Exception as e:
        app.logger.error(f"Image generation endpoint failed: {str(e)}", exc_info=True)
        return {"success": False, "error": f"Image generation failed: {str(e)}"}, 500

@app.route("/generate-bulk-images", methods=["POST"])
def generate_bulk_images():
    """Generate images for multiple posts at once."""
    try:
        # Run cleanup before generating new images
        cleanup_old_images()
        
        data = request.get_json()
        posts = data.get('posts', [])
        book_title = data.get('book_title', 'children\'s book')
        
        if not posts:
            return {"success": False, "error": "No posts provided"}, 400
        
        # Get brand assets from session
        brand_assets = session.get('brand_assets', {})
        app.logger.debug(f"Using brand assets for bulk generation: {brand_assets}")
        
        results = []
        for i, post in enumerate(posts):
            try:
                image_idea = post.get('image_idea', '').strip()
                theme = post.get('theme', 'social_media')
                
                if image_idea:
                    app.logger.info(f"Generating bulk image {i+1}/{len(posts)}: {image_idea}")
                    result = image_generator.create_social_media_image(
                        image_idea=image_idea,
                        book_title=book_title,
                        post_theme=theme,
                        brand_assets=brand_assets
                    )
                    results.append({
                        'index': i,
                        'image_idea': image_idea,
                        'result': result
                    })
                else:
                    results.append({
                        'index': i,
                        'image_idea': '',
                        'result': {'success': False, 'error': 'No image idea provided'}
                    })
                    
            except Exception as e:
                app.logger.error(f"Failed to generate image for post {i}: {str(e)}")
                results.append({
                    'index': i,
                    'result': {'success': False, 'error': str(e)}
                })
        
        return {
            "success": True, 
            "results": results,
            "total_processed": len(posts),
            "successful_generations": sum(1 for r in results if r['result'].get('success', False))
        }
        
    except Exception as e:
        app.logger.error(f"Bulk image generation failed: {str(e)}")
        return {"success": False, "error": "Bulk generation failed"}, 500

@app.route("/generate-batch-images", methods=["POST"])
def generate_batch_images():
    """Generate images for a batch of posts (5 at a time to avoid timeout)."""
    try:
        data = request.get_json()
        start_index = data.get('start_index', 0)
        batch_size = data.get('batch_size', 5)
        
        # Get calendar session ID from session
        calendar_session_id = session.get('calendar_session_id')
        if not calendar_session_id:
            return {"success": False, "error": "No calendar session found"}, 400
        
        # Get posts from database
        calendar = GeneratedCalendar.query.filter_by(session_id=calendar_session_id).first()
        if not calendar:
            return {"success": False, "error": "Calendar not found in database"}, 404
        
        posts = json.loads(calendar.posts_json)
        book_title = calendar.book_title or 'children\'s book'
        brand_assets = json.loads(calendar.brand_assets_json) if calendar.brand_assets_json else {}
        
        if not posts:
            return {"success": False, "error": "No posts found in session"}, 400
        
        # Calculate batch boundaries
        end_index = min(start_index + batch_size, len(posts))
        batch_posts = posts[start_index:end_index]
        
        app.logger.info(f"Generating batch images {start_index}-{end_index-1} ({len(batch_posts)} posts)")
        
        results = []
        for i, post in enumerate(batch_posts):
            actual_index = start_index + i
            try:
                image_idea = post.get('image_idea', '').strip()
                theme = post.get('theme', 'social_media')
                hook = post.get('hook', '').strip()
                
                if image_idea:
                    app.logger.info(f"Generating image {actual_index + 1}/{len(posts)}: {image_idea}")
                    result = image_generator.create_social_media_image(
                        image_idea=image_idea,
                        book_title=book_title,
                        post_theme=theme,
                        hook=hook,
                        brand_assets=brand_assets
                    )
                    
                    # Update the post with image URLs
                    if result and result.get('success'):
                        posts[actual_index]['image_url'] = result.get('image_url', '')
                        posts[actual_index]['image_path'] = result.get('image_path', '')
                    
                    results.append({
                        'index': actual_index,
                        'image_idea': image_idea,
                        'result': result
                    })
                else:
                    results.append({
                        'index': actual_index,
                        'image_idea': '',
                        'result': {'success': False, 'error': 'No image idea provided'}
                    })
                    
            except Exception as e:
                app.logger.error(f"Failed to generate image for post {actual_index}: {str(e)}")
                results.append({
                    'index': actual_index,
                    'result': {'success': False, 'error': str(e)}
                })
        
        # Save updated posts back to database with image URLs
        calendar.posts_json = json.dumps(posts)
        db.session.commit()
        app.logger.info(f"Updated calendar JSON with image URLs for batch {start_index}-{end_index-1}")
        
        return {
            "success": True, 
            "results": results,
            "batch_start": start_index,
            "batch_end": end_index,
            "total_posts": len(posts),
            "completed": end_index >= len(posts)
        }
        
    except Exception as e:
        app.logger.error(f"Batch image generation failed: {str(e)}")
        return {"success": False, "error": str(e)}, 500

@app.route("/download-images-zip", methods=["POST"])
def download_images_zip():
    """Download all generated images as a ZIP file with numbered filenames."""
    try:
        app.logger.debug(f"ZIP download request received. Form data keys: {list(request.form.keys())}")
        rows = int(request.form["rows_count"])
        app.logger.info(f"Processing ZIP download for {rows} rows")
        
        # Trusted image host domains (DALL-E CDN and other allowed sources)
        TRUSTED_DOMAINS = [
            'oaidalleapiprodscus.blob.core.windows.net',  # OpenAI DALL-E CDN
            'dalleprodsec.blob.core.windows.net'           # OpenAI DALL-E alternative CDN
        ]
        
        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            images_found = 0
            
            for i in range(rows):
                image_url = request.form.get(f"image_url_{i}", "").strip()
                app.logger.debug(f"Row {i}: image_url_{i} = '{image_url}'")
                
                if image_url:
                    try:
                        # Check if it's a local static file path
                        if image_url.startswith('/static/images/'):
                            # Local image - read directly from filesystem
                            image_path = image_url.lstrip('/')  # Remove leading slash
                            full_path = os.path.join(app.root_path, image_path)
                            
                            if os.path.exists(full_path):
                                with open(full_path, 'rb') as img_file:
                                    image_data = img_file.read()
                                
                                # Get extension from filename
                                ext = image_url.split('.')[-1] if '.' in image_url else 'png'
                                
                                # Add to ZIP with numbered filename
                                filename = f"post_{i+1:02d}.{ext}"
                                zip_file.writestr(filename, image_data)
                                images_found += 1
                                app.logger.info(f"Added local image {filename} to ZIP")
                            else:
                                app.logger.warning(f"Local image not found: {full_path}")
                                continue
                        else:
                            # Remote URL - validate and download
                            parsed_url = urlparse(image_url)
                            
                            # Normalize hostname: lowercase and strip trailing dots to prevent bypass
                            normalized_host = parsed_url.netloc.lower().rstrip('.')
                            
                            if normalized_host not in TRUSTED_DOMAINS:
                                app.logger.warning(f"Rejecting untrusted image URL from domain: {normalized_host}")
                                continue
                            
                            # Security: Only allow HTTPS
                            if parsed_url.scheme != 'https':
                                app.logger.warning(f"Rejecting non-HTTPS image URL: {image_url}")
                                continue
                            
                            # Download the image with timeout and size limits
                            app.logger.info(f"Downloading image {i+1} from trusted source: {parsed_url.netloc}")
                            response = requests.get(
                                image_url, 
                                timeout=30,
                                stream=True  # Stream to check size before downloading
                            )
                            response.raise_for_status()
                            
                            # Security: Check content length before downloading
                            content_length = int(response.headers.get('content-length', 0))
                            MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB limit
                            if content_length > MAX_IMAGE_SIZE:
                                app.logger.warning(f"Image {i+1} too large: {content_length} bytes")
                                continue
                            
                            # Download content with size enforcement
                            image_data = b''
                            for chunk in response.iter_content(chunk_size=8192):
                                image_data += chunk
                                if len(image_data) > MAX_IMAGE_SIZE:
                                    app.logger.warning(f"Image {i+1} exceeded size limit during download")
                                    raise ValueError("Image too large")
                            
                            # Determine file extension from URL or content type
                            content_type = response.headers.get('content-type', '')
                            if 'png' in content_type:
                                ext = 'png'
                            elif 'jpg' in content_type or 'jpeg' in content_type:
                                ext = 'jpg'
                            else:
                                # Try to get from URL
                                path = parsed_url.path
                                ext = path.split('.')[-1] if '.' in path else 'png'
                            
                            # Add to ZIP with numbered filename (1-indexed to match spreadsheet row numbers)
                            filename = f"post_{i+1:02d}.{ext}"
                            zip_file.writestr(filename, image_data)
                            images_found += 1
                            app.logger.info(f"Added remote image {filename} to ZIP")
                        
                    except Exception as img_error:
                        app.logger.error(f"Failed to download image {i+1}: {str(img_error)}")
                        # Continue with other images even if one fails
            
            # Add a README file with instructions
            readme_content = f"""Social Media Calendar Images
============================

This ZIP contains {images_found} images generated for your social media calendar.

Filenames are numbered to match the row numbers in your spreadsheet:
- post_01.png corresponds to Row 1
- post_02.png corresponds to Row 2
- etc.

Simply upload these images when scheduling your posts in your social media tool of choice.

Generated by Self-Publishing Made Simple™
"""
            zip_file.writestr("README.txt", readme_content)
        
        zip_buffer.seek(0)
        
        if images_found == 0:
            return "<h3>No Images Found</h3><p>Please generate images first before downloading the ZIP file.</p><a href='javascript:history.back()'>Go Back</a>", 400
        
        # Generate filename with timestamp
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
        filename = f"social_media_images_{timestamp}.zip"
        
        app.logger.info(f"Sending ZIP file with {images_found} images")
        
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error creating images ZIP: {str(e)}")
        return f"<h3>Error creating ZIP file</h3><p>Error: {str(e)}</p><a href='javascript:history.back()'>Go Back</a>", 500

@app.route("/campaign/<int:campaign_id>/preview")
def campaign_preview(campaign_id):
    """Reconstruct preview page from a saved campaign."""
    campaign = Campaign.query.get_or_404(campaign_id)
    posts_query = ScheduledPost.query.filter_by(campaign_id=campaign_id).order_by(ScheduledPost.post_date).all()
    
    # Convert posts to preview format
    rows = []
    for post in posts_query:
        rows.append({
            'Date': post.post_date.strftime('%Y-%m-%d'),
            'Hook': post.hook or '',
            'Caption': post.caption or '',
            'Hashtags': post.hashtags or '',
            'Image Idea': '',  # Not stored in ScheduledPost
            'Theme': post.theme or '',
            'CTA': post.cta or '',
            'image_url': post.image_url or ''
        })
    
    return render_template("preview.html", 
                         rows=rows,
                         campaign_id=campaign_id,
                         campaign_name=campaign.name)

@app.route("/planner/<int:campaign_id>")
def planner(campaign_id):
    """Display visual content planner with calendar grid and Instagram feed preview."""
    campaign = Campaign.query.get_or_404(campaign_id)
    posts_query = ScheduledPost.query.filter_by(campaign_id=campaign_id).order_by(ScheduledPost.post_date).all()
    
    # Convert posts to dictionaries for JSON serialization
    posts = []
    for post in posts_query:
        posts.append({
            'id': post.id,
            'post_date': post.post_date.isoformat(),
            'theme': post.theme,
            'caption': post.caption,
            'hashtags': post.hashtags,
            'image_url': post.image_url,
            'hook': post.hook,
            'cta': post.cta,
            'status': post.status
        })
    
    # Parse brand assets from JSON
    brand_assets = json.loads(campaign.brand_assets_json) if campaign.brand_assets_json else {}
    
    return render_template("planner.html", 
                         campaign=campaign, 
                         posts=posts,
                         brand_assets=brand_assets)

@app.route("/campaign/<int:campaign_id>/delete-all-posts", methods=["POST"])
def delete_all_posts(campaign_id):
    """Delete all scheduled posts from a campaign (for testing/reset purposes)."""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Delete all posts associated with this campaign
        deleted_count = ScheduledPost.query.filter_by(campaign_id=campaign_id).delete()
        db.session.commit()
        
        app.logger.info(f"Deleted {deleted_count} posts from campaign {campaign_id}")
        
        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Successfully deleted {deleted_count} posts'
        })
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting posts: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route("/save-to-planner", methods=["POST"])
def save_to_planner():
    """Save generated posts to database as a campaign and redirect to planner."""
    try:
        # Get calendar session from database
        calendar_session_id = session.get('calendar_session_id')
        if not calendar_session_id:
            return jsonify({'success': False, 'error': 'No calendar session found'}), 400
        
        calendar = GeneratedCalendar.query.filter_by(session_id=calendar_session_id).first()
        if not calendar:
            return jsonify({'success': False, 'error': 'Calendar not found'}), 404
        
        # Parse stored data
        posts = json.loads(calendar.posts_json)
        brand_assets = json.loads(calendar.brand_assets_json) if calendar.brand_assets_json else {}
        
        # Get start date and cadence from request or use defaults
        start_date_str = request.json.get('start_date')
        cadence = request.json.get('cadence', 'daily')
        
        if start_date_str:
            from datetime import datetime
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = d.today()
        
        # Create campaign
        campaign = Campaign(
            name=f"{calendar.book_title} - {start_date.strftime('%b %Y')}",
            book_title=calendar.book_title,
            start_date=start_date,
            cadence=cadence,
            brand_assets_json=calendar.brand_assets_json
        )
        db.session.add(campaign)
        db.session.flush()  # Get campaign ID
        
        # Generate dates and create scheduled posts
        dates = build_date_series(start_date, len(posts), cadence=cadence)
        
        for i, (post_data, post_date) in enumerate(zip(posts, dates)):
            # Parse datetime string to date, then set default time (9am)
            from datetime import datetime, time
            if isinstance(post_date, str):
                post_date = datetime.strptime(post_date, '%Y-%m-%d').date()
            
            # Create datetime with default 9am posting time
            post_datetime = datetime.combine(post_date, time(9, 0))
            
            scheduled_post = ScheduledPost(
                campaign_id=campaign.id,
                post_date=post_datetime,
                theme=post_data.get('theme', ''),
                caption=post_data.get('caption', ''),
                hashtags=post_data.get('hashtags', ''),
                image_url=post_data.get('image_url', ''),
                image_path=post_data.get('image_path', ''),
                hook=post_data.get('hook', ''),
                cta=post_data.get('cta', ''),
                status='draft'
            )
            db.session.add(scheduled_post)
        
        db.session.commit()
        app.logger.info(f"Created campaign {campaign.id} with {len(posts)} scheduled posts")
        
        return jsonify({
            'success': True,
            'campaign_id': campaign.id,
            'redirect_url': url_for('planner', campaign_id=campaign.id)
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error saving to planner: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/update-post-date", methods=["POST"])
def update_post_date():
    """Update a post's date when dragged to a new calendar day."""
    try:
        data = request.json
        post_id = data.get('post_id')
        new_date_str = data.get('new_date')
        
        if not post_id or not new_date_str:
            return jsonify({'success': False, 'error': 'Missing post_id or new_date'}), 400
        
        # Get the post
        post = ScheduledPost.query.get(post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        # Parse new date and preserve the time
        from datetime import datetime
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        old_time = post.post_date.time()
        
        # Create new datetime with old time
        new_datetime = datetime.combine(new_date, old_time)
        
        # Update post date
        post.post_date = new_datetime
        db.session.commit()
        
        app.logger.info(f"Updated post {post_id} to date {new_date_str}")
        
        return jsonify({
            'success': True,
            'post_id': post_id,
            'new_date': new_datetime.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating post date: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/update-post", methods=["POST"])
def update_post():
    """Update post content fields (caption, hook, hashtags, theme, cta)."""
    try:
        data = request.json
        post_id = data.get('post_id')
        
        if not post_id:
            return jsonify({'success': False, 'error': 'Missing post_id'}), 400
        
        # Get the post
        post = ScheduledPost.query.get(post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        # Update fields
        if 'caption' in data:
            post.caption = data['caption']
        if 'hook' in data:
            post.hook = data['hook']
        if 'image_idea' in data:
            post.image_idea = data['image_idea']
        if 'hashtags' in data:
            post.hashtags = data['hashtags']
        if 'theme' in data:
            post.theme = data['theme']
        if 'cta' in data:
            post.cta = data['cta']
        
        db.session.commit()
        
        app.logger.info(f"Updated post {post_id} content")
        
        return jsonify({
            'success': True,
            'post_id': post_id
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error updating post: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/regenerate-post-image", methods=["POST"])
def regenerate_post_image():
    """Regenerate the image for a single post."""
    try:
        data = request.json
        post_id = data.get('post_id')
        campaign_id = data.get('campaign_id')
        
        if not post_id or not campaign_id:
            return jsonify({'success': False, 'error': 'Missing post_id or campaign_id'}), 400
        
        # Get the post and campaign
        post = ScheduledPost.query.get(post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        campaign = Campaign.query.get(campaign_id)
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Parse brand assets
        brand_assets = {}
        if campaign.brand_assets_json:
            brand_assets = json.loads(campaign.brand_assets_json)
        
        # Generate new image
        from image_generator import generate_single_image
        
        app.logger.info(f"Regenerating image for post {post_id}")
        
        # Get updated image_idea and hook from request if provided
        image_idea = data.get('image_idea') or post.image_idea or f"{post.theme} post for {campaign.book_title}"
        hook = data.get('hook') or post.hook or ''
        
        # Create post data dict for image generation
        post_data = {
            'hook': hook,
            'caption': post.caption,
            'theme': post.theme,
            'image_idea': image_idea
        }
        
        image_result = generate_single_image(post_data, brand_assets)
        
        if image_result and image_result.get('image_url'):
            # Update post with new image
            post.image_url = image_result['image_url']
            post.image_path = image_result.get('image_path', '')
            db.session.commit()
            
            app.logger.info(f"Successfully regenerated image for post {post_id}")
            
            return jsonify({
                'success': True,
                'post_id': post_id,
                'image_url': image_result['image_url']
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate image'}), 500
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error regenerating image: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/delete-post", methods=["POST"])
def delete_post():
    """Delete a scheduled post."""
    try:
        data = request.json
        post_id = data.get('post_id')
        
        if not post_id:
            return jsonify({'success': False, 'error': 'Missing post_id'}), 400
        
        # Get the post
        post = ScheduledPost.query.get(post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        # Delete the post
        db.session.delete(post)
        db.session.commit()
        
        app.logger.info(f"Deleted post {post_id}")
        
        return jsonify({
            'success': True,
            'post_id': post_id
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting post: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/upload-custom-image", methods=["POST"])
def upload_custom_image():
    """Handle custom image upload to replace AI-generated images."""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload PNG, JPG, GIF, or WebP'}), 400
        
        # Check file size (already validated client-side, but double-check server-side)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'File size exceeds 10MB limit'}), 400
        
        # Generate secure filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        original_ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"custom_{timestamp}.{original_ext}"
        filename = secure_filename(filename)
        
        # Ensure images directory exists
        images_dir = os.path.join('static', 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        # Save file
        filepath = os.path.join(images_dir, filename)
        file.save(filepath)
        
        # Generate public URL
        image_url = url_for('static', filename=f'images/{filename}', _external=False)
        
        app.logger.info(f"Custom image uploaded: {filename}")
        
        return jsonify({
            'success': True,
            'image_url': image_url,
            'filename': filename
        })
        
    except Exception as e:
        app.logger.error(f"Error uploading custom image: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/instagram/connect/<int:campaign_id>")
def instagram_connect(campaign_id):
    """Initiate Instagram OAuth flow."""
    from instagram_api import InstagramAPI
    import secrets
    
    # Check if required environment variables are set
    if not os.environ.get('FACEBOOK_APP_ID') or not os.environ.get('FACEBOOK_APP_SECRET'):
        flash("Instagram integration not configured. Please add FACEBOOK_APP_ID and FACEBOOK_APP_SECRET environment variables.", "error")
        return redirect(url_for('planner', campaign_id=campaign_id))
    
    campaign = Campaign.query.get_or_404(campaign_id)
    
    # Generate CSRF token
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    session['oauth_campaign_id'] = campaign_id
    
    # Get redirect URI from environment or use current domain
    redirect_uri = os.environ.get('INSTAGRAM_REDIRECT_URI') or url_for('instagram_callback', _external=True)
    
    # Generate auth URL
    auth_url = InstagramAPI.get_auth_url(redirect_uri, state)
    
    return redirect(auth_url)

@app.route("/instagram/callback")
def instagram_callback():
    """Handle Instagram OAuth callback."""
    from instagram_api import InstagramAPI, InstagramAPIError
    
    # Check for errors
    error = request.args.get('error')
    if error:
        error_description = request.args.get('error_description', 'Unknown error')
        app.logger.error(f"Instagram OAuth error: {error} - {error_description}")
        flash(f"Instagram connection failed: {error_description}", "error")
        return redirect(url_for('index'))
    
    # Verify CSRF token
    state = request.args.get('state')
    if state != session.get('oauth_state'):
        flash("Invalid OAuth state. Please try again.", "error")
        return redirect(url_for('index'))
    
    # Get authorization code
    code = request.args.get('code')
    if not code:
        flash("No authorization code received from Instagram.", "error")
        return redirect(url_for('index'))
    
    campaign_id = session.get('oauth_campaign_id')
    if not campaign_id:
        flash("Session expired. Please try again.", "error")
        return redirect(url_for('index'))
    
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Exchange code for access token
        redirect_uri = os.environ.get('INSTAGRAM_REDIRECT_URI') or url_for('instagram_callback', _external=True)
        token_data = InstagramAPI.exchange_code_for_token(code, redirect_uri)
        
        # Get Instagram profile info
        api = InstagramAPI(token_data['access_token'])
        profile = api.get_profile()
        
        # Save credentials to campaign
        campaign.instagram_access_token = token_data['access_token']
        campaign.instagram_user_id = profile['id']
        campaign.instagram_username = profile.get('username')
        campaign.instagram_token_expires = token_data['expires_at']
        campaign.instagram_connected = True
        
        db.session.commit()
        
        app.logger.info(f"Instagram connected for campaign {campaign_id}: @{profile.get('username')}")
        flash(f"Successfully connected Instagram account @{profile.get('username')}!", "success")
        
        # Clear session
        session.pop('oauth_state', None)
        session.pop('oauth_campaign_id', None)
        
        return redirect(url_for('planner', campaign_id=campaign_id))
        
    except InstagramAPIError as e:
        app.logger.error(f"Instagram OAuth failed: {str(e)}")
        flash(f"Failed to connect Instagram: {str(e)}", "error")
        return redirect(url_for('index'))
    except Exception as e:
        app.logger.error(f"Unexpected error in Instagram OAuth: {str(e)}", exc_info=True)
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('index'))

@app.route("/instagram/disconnect/<int:campaign_id>", methods=["POST"])
def instagram_disconnect(campaign_id):
    """Disconnect Instagram account from campaign."""
    try:
        campaign = Campaign.query.get_or_404(campaign_id)
        
        # Clear Instagram credentials
        campaign.instagram_access_token = None
        campaign.instagram_user_id = None
        campaign.instagram_username = None
        campaign.instagram_token_expires = None
        campaign.instagram_connected = False
        
        db.session.commit()
        
        app.logger.info(f"Instagram disconnected for campaign {campaign_id}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error disconnecting Instagram: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/instagram/publish-post", methods=["POST"])
def instagram_publish_post():
    """Publish a single post to Instagram immediately."""
    from instagram_api import InstagramAPI, InstagramAPIError
    
    try:
        data = request.json
        post_id = data.get('post_id')
        
        if not post_id:
            return jsonify({'success': False, 'error': 'Missing post_id'}), 400
        
        # Get the post
        post = ScheduledPost.query.get(post_id)
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        # Get campaign and check Instagram connection
        campaign = post.campaign
        if not campaign.instagram_connected or not campaign.instagram_access_token:
            return jsonify({'success': False, 'error': 'Instagram not connected. Please connect your Instagram account first.'}), 400
        
        # Check if post has image
        if not post.image_url:
            return jsonify({'success': False, 'error': 'Post must have an image to publish to Instagram'}), 400
        
        # Build full image URL
        image_url = post.image_url
        if not image_url.startswith('http'):
            image_url = url_for('static', filename=post.image_url.replace('/static/', ''), _external=True)
        
        # Build caption
        caption = f"{post.caption}\n\n{post.hashtags}"
        
        # Publish to Instagram
        api = InstagramAPI(campaign.instagram_access_token)
        media_id = api.publish_post(image_url, caption)
        
        # Update post status
        post.status = 'published'
        post.instagram_post_id = media_id
        post.published_at = datetime.utcnow()
        post.error_message = None
        
        db.session.commit()
        
        app.logger.info(f"Published post {post_id} to Instagram: {media_id}")
        
        return jsonify({
            'success': True,
            'media_id': media_id,
            'message': 'Post published to Instagram successfully!'
        })
        
    except InstagramAPIError as e:
        # Update post with error
        if 'post' in locals():
            post.status = 'failed'
            post.error_message = str(e)
            db.session.commit()
        
        app.logger.error(f"Instagram publish failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error publishing to Instagram: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template("form.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return "<h3>Internal Server Error</h3><p>Something went wrong. Please try again.</p>", 500
