from datetime import datetime
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class BookForm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_title = db.Column(db.String(200), nullable=False)
    age_range = db.Column(db.String(50), default="ages 4–8")
    audience = db.Column(db.String(200), default="families, educators, authors")
    tone = db.Column(db.String(50), default="Warm")
    goal = db.Column(db.Text)
    themes = db.Column(db.String(200), default="courage, kindness, friendship")
    differentiator = db.Column(db.Text)
    events = db.Column(db.Text)
    additional_context = db.Column(db.Text)
    start_date = db.Column(db.String(20))
    cadence = db.Column(db.String(20), default="daily")
    primary_color = db.Column(db.String(20), default="#FF6B6B")
    secondary_color = db.Column(db.String(20), default="#4ECDC4")
    background_color = db.Column(db.String(20), default="#F7F7F7")
    heading_font = db.Column(db.String(100), default="Playfair Display")
    body_font = db.Column(db.String(100), default="Open Sans")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'book_title': self.book_title,
            'age_range': self.age_range,
            'audience': self.audience,
            'tone': self.tone,
            'goal': self.goal,
            'themes': self.themes,
            'differentiator': self.differentiator,
            'events': self.events,
            'additional_context': self.additional_context,
            'start_date': self.start_date,
            'cadence': self.cadence,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'background_color': self.background_color,
            'heading_font': self.heading_font,
            'body_font': self.body_font,
            'created_at': self.created_at
        }

class GeneratedCalendar(db.Model):
    """Store generated social media posts to avoid session size limits"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    book_title = db.Column(db.String(200))
    posts_json = db.Column(db.Text, nullable=False)  # JSON array of posts
    brand_assets_json = db.Column(db.Text)  # JSON object of brand assets
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Campaign(db.Model):
    """Campaign tracks a complete 30-day social media calendar"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    book_title = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    cadence = db.Column(db.String(20), default="daily")
    brand_assets_json = db.Column(db.Text)
    instagram_connected = db.Column(db.Boolean, default=False)
    instagram_user_id = db.Column(db.String(100))
    instagram_username = db.Column(db.String(100))
    instagram_access_token = db.Column(db.String(500))
    instagram_token_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    posts = db.relationship('ScheduledPost', backref='campaign', lazy=True, cascade='all, delete-orphan')

class ScheduledPost(db.Model):
    """Individual scheduled social media post"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    post_date = db.Column(db.DateTime, nullable=False, index=True)
    theme = db.Column(db.String(50))
    caption = db.Column(db.Text, nullable=False)
    hashtags = db.Column(db.String(500))
    image_url = db.Column(db.String(500))
    image_path = db.Column(db.String(500))
    image_idea = db.Column(db.Text)  # Description of what the image should show
    hook = db.Column(db.String(200))
    cta = db.Column(db.String(200))
    status = db.Column(db.String(20), default='draft')  # draft, scheduled, published, failed
    instagram_post_id = db.Column(db.String(100))
    error_message = db.Column(db.Text)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)