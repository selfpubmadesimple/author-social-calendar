# fallback_posts.py - Fallback content generation when OpenAI API is unavailable
import logging
from datetime import date

def generate_fallback_posts(inputs: dict, num_days: int = 30, holidays = None):
    """
    Generate fallback social media posts when OpenAI API is unavailable.
    Creates a variety of posts using templates and book information.
    """
    logging.info(f"Generating fallback posts for {inputs.get('book_title', 'book')}")
    
    book_title = inputs.get('book_title', 'your book')
    themes = inputs.get('themes', 'courage, kindness, friendship').split(',')
    themes = [t.strip() for t in themes[:3]]  # Take first 3 themes
    age_range = inputs.get('age_range', 'ages 4–8')
    
    # Holiday context
    holiday_context = ""
    if holidays:
        current_holidays = [h['name'] for h in holidays[:2]]  # Take first 2
        holiday_context = f" Perfect for {' and '.join(current_holidays)} season!"
    
    posts = []
    theme_cycle = ['value', 'bts', 'quote', 'engagement', 'promo']
    
    # VALUE posts templates
    value_templates = [
        {
            "caption": f"Reading {book_title} together creates lasting memories for families.{holiday_context} Set aside 15 minutes each day for shared reading time.",
            "hook": "Family reading time builds bonds",
            "hashtags": "#KidLit #PictureBook #FamilyReading #ReadAloud #ParentingTips",
            "image_idea": "Cozy reading corner with book and warm lighting",
            "cta": "Start your family reading time today!"
        },
        {
            "caption": f"Teachers love using {book_title} to explore {themes[0] if themes else 'important values'} with students. Great for classroom discussions and activities.",
            "hook": "Classroom connection opportunity",
            "hashtags": "#KidLit #TeacherLife #ClassroomBooks #ChildrensLit #Education",
            "image_idea": "Book displayed on classroom reading table",
            "cta": "Perfect for your classroom library"
        }
    ]
    
    # BTS posts templates  
    bts_templates = [
        {
            "caption": f"Behind the scenes: Creating {book_title} took months of research and countless drafts. Every word was chosen to resonate with {age_range} readers.",
            "hook": "The writing process revealed",
            "hashtags": "#KidLit #WritingLife #AuthorJourney #PictureBook #CreativeProcess",
            "image_idea": "Writer's desk with manuscripts and coffee",
            "cta": "Follow the writing journey"
        },
        {
            "caption": f"Fun fact: The main character in {book_title} was inspired by real children I met during school visits. Their curiosity shapes every story.",
            "hook": "Character inspiration story",
            "hashtags": "#KidLit #AuthorLife #CharacterDevelopment #SchoolVisits #Inspiration",
            "image_idea": "Author notebook with character sketches",
            "cta": "Book a school visit"
        }
    ]
    
    # QUOTE posts templates
    quote_templates = [
        {
            "caption": f"From {book_title}: 'Sometimes the biggest adventures happen in the quietest moments.' Perfect for bedtime reading with little ones.",
            "hook": "A favorite line from the story",
            "hashtags": "#KidLit #PictureBook #BedtimeStory #QuietMoments #ChildrensBooks",
            "image_idea": "Open book with soft bedside lamp",
            "cta": "Perfect for bedtime stories"
        },
        {
            "caption": f"Readers say: 'My child asks for {book_title} every single night!' Stories that stick with kids become treasured memories.",
            "hook": "What parents are saying",
            "hashtags": "#KidLit #ParentReviews #BedtimeReading #FavoriteBooks #ChildrensLit",
            "image_idea": "Child holding the book with a big smile",
            "cta": "Get your copy today"
        }
    ]
    
    # ENGAGEMENT posts templates
    engagement_templates = [
        {
            "caption": f"What's your family's favorite reading spot? Share a photo of where you enjoy {book_title} together! We love seeing cozy reading nooks.",
            "hook": "Show us your reading space",
            "hashtags": "#KidLit #ReadingNook #FamilyReading #ShareYourSpace #BookLovers",
            "image_idea": "Multiple cozy reading spaces collage",
            "cta": "Share your reading nook photo!"
        },
        {
            "caption": f"Teachers: How do you use {book_title} in your classroom? Share your creative lesson ideas and activities in the comments below!",
            "hook": "Calling all educators",
            "hashtags": "#KidLit #TeacherLife #ClassroomActivities #Education #LessonPlans",
            "image_idea": "Classroom bulletin board with book theme",
            "cta": "Share your lesson ideas below"
        }
    ]
    
    # PROMO posts templates
    promo_templates = [
        {
            "caption": f"Libraries are ordering {book_title} for their collections!{holiday_context} Ask your local librarian about adding it to story time.",
            "hook": "Coming to libraries near you",
            "hashtags": "#KidLit #LibraryBooks #Storytime #PictureBook #NewBooks",
            "image_idea": "Book on library display with other picture books",
            "cta": "Ask your librarian about story time!"
        },
        {
            "caption": f"Bookstores report {book_title} flying off shelves. Perfect gift for young readers who love stories about {themes[0] if themes else 'friendship'}.",
            "hook": "Popular with young readers",
            "hashtags": "#KidLit #GiftBooks #Bookstore #ChildrensBooks #PopularPicks",
            "image_idea": "Bookstore shelf with book prominently displayed",
            "cta": "Find it at your local bookstore"
        }
    ]
    
    # Combine all templates
    all_templates = {
        'value': value_templates * 3,  # Repeat to have enough
        'bts': bts_templates * 3,
        'quote': quote_templates * 3,
        'engagement': engagement_templates * 3,
        'promo': promo_templates * 3
    }
    
    # Generate posts following the theme distribution
    for i in range(num_days):
        theme = theme_cycle[i % 5]
        template_idx = (i // 5) % len(all_templates[theme])
        template = all_templates[theme][template_idx]
        
        post = {
            "theme": theme,
            "caption": template["caption"][:280],  # Ensure length limit
            "hashtags": template["hashtags"],
            "image_idea": template["image_idea"],
            "hook": template["hook"],
            "cta": template.get("cta", ""),
            "image_url": "",  # Will be filled in if images are generated
            "image_path": ""
        }
        
        posts.append(post)
    
    logging.info(f"Generated {len(posts)} fallback posts")
    return posts[:num_days]