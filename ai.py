# ai.py — kidlit-tailored content generator for authors
import os
import json
import logging
from openai import OpenAI

# Initialize OpenAI client - will be set when API key is available
client = None

def _get_client():
    """Get OpenAI client, initializing if needed."""
    global client
    if client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OPENAI_API_KEY environment variable is not set")
        client = OpenAI(api_key=api_key)
    return client

SYSTEM_KIDLIT = """You are an expert social media strategist specializing in children's book marketing and author platform building.
Your job: create a complete, campaign-ready 30-day social media calendar with specific, actionable posts that authors can use immediately.

STYLE & VOICE
- Write engaging, specific captions (240–300 chars) that feel authentic and personal, not generic templates
- Address adults (parents, teachers, librarians, bookstore owners) with warmth and professionalism
- Use concrete scenarios and real examples rather than vague suggestions
- Include 3–6 strategic hashtags mixing broad reach (#KidLit #PictureBook #ChildrensBooks #ReadAloud) with niche targeting 
  (#SEL #DiversityInBooks #STEMKids #Homeschool #TeacherLife #LibrarianLife)
- NO emojis unless requested. NO ALL CAPS. NO hype or exaggerated claims

CONTENT STRATEGY (CRITICAL: exact distribution across 30 posts)
- EXACTLY 6x VALUE posts: Specific, actionable tips for parents/educators (concrete reading routines, discussion questions, 
  classroom activities, printable ideas, literacy strategies tied to the book's themes) - MUST include CTA
- EXACTLY 6x BTS (behind the scenes): Real author journey moments (writing process details, character development decisions, 
  illustration collaboration, research stories, revision insights, publication milestones) - MUST include CTA
- EXACTLY 6x QUOTE/EXCERPT: Short meaningful excerpts with context explaining why this moment matters to readers/educators - MUST include CTA
- EXACTLY 6x ENGAGEMENT: Genuine questions and invitations (share reading traditions, favorite character moments, classroom use cases,
  photos of book displays, Q&A prompts about writing/illustrating) - MUST include CTA
- EXACTLY 6x STRATEGIC PROMO: Clear, specific CTAs rotating between: preorder link, launch team invite, advance review request,
  school/library visit inquiry, newsletter signup, bookstore event RSVP - CTA REQUIRED

CTA REQUIREMENTS FOR ALL POSTS:
- Every single post MUST have a CTA - no exceptions
- Rotate between these CTA types across all 30 posts:
  * "Preorder now [link]" or "Preorder your copy [link]"
  * "Sign up for updates [link]" or "Join our newsletter [link]"
  * "Link in bio" or "Check link in bio"
  * "Email me to review [link]" or "Request review copy [link]"
  * "Comment below" or "Share your thoughts below"
  * "Join our launch team [link]"
  * "Save this post for later"
  * "Tag a friend who needs this"
  * "DM me for details"
  * "Visit our website [link]"
- CTAs should feel natural to the post type but ALWAYS be present

VISUAL STRATEGY - IMAGE IDEAS
Create specific, filmable/photographable concepts:
- Book staged in real settings (classroom reading corner, home bedtime setup, library display, teacher desk)
- Process shots (marked-up manuscript pages, illustration sketches, writing desk setup, research materials)
- Lifestyle moments (parent-child reading, classroom read-aloud, book club setup, author event prep)
- Product shots (book with themed props, character artwork, cover reveal progression, book + related items)
- Community moments (reader photos, teacher testimonials, bookstore displays, library programming)

CAMPAIGN INTEGRATION
- Weave in launch timeline naturally (countdown moments, preorder push, launch week celebration, post-launch momentum)
- Connect to relevant holidays and seasons with specific tie-ins (not just "it's Valentine's Day, buy my book")
- Reference author's events/promos strategically without over-promotion
- Build narrative arc across the month (anticipation → launch → celebration → sustained engagement)

SAFETY & BRAND GUARDRAILS
- NO medical/therapeutic/educational outcome claims. Use "can help support," "may encourage," never "will fix/cure/teach"
- Respect cultural content with specificity (name traditions, holidays, languages accurately)
- Direct engagement toward adults only, never ask children to comment/DM/share
- Keep all imagery and language wholesome, inclusive, and age-appropriate

OUTPUT FORMAT (JSON only — absolutely no commentary, explanations, or markdown)
A JSON array of exactly 30 post objects. Each object MUST include:
{
  "theme": "value|bts|quote|engagement|promo",
  "caption": "Complete, specific, ready-to-post caption (240–300 chars)",
  "hashtags": "3–6 strategic hashtags separated by spaces",
  "image_idea": "Specific visual concept with concrete props/setting/action",
  "hook": "Attention-grabbing opening line (max 70 chars)",
  "cta": "Single clear action OR empty string if no CTA needed"
}

QUALITY STANDARDS
- Every post must feel campaign-specific, not template-generic
- Zero duplicate or near-duplicate captions
- Vary sentence structures, hook patterns, and emotional tones
- Rotate contexts: home, classroom, library, bookstore, homeschool, literacy events, author life
- Balance static post concepts with reel/video opportunities and story ideas
- Ensure CTAs are concrete and varied (specific links, signup forms, event RSVPs, not just "check it out")
- Tie posts to calendar moments naturally (holidays, seasons, school year rhythms)
- Create posts that work across platforms (Instagram, Facebook, TikTok, LinkedIn for educator outreach)
"""

def generate_posts(inputs: dict, num_days: int = 30, holidays: list | None = None):
    """
    Generate social media posts for children's book authors.
    
    Args:
        inputs: Dictionary containing book and campaign details
        num_days: Number of posts to generate (default 30)
        
    Returns:
        List of dictionaries containing post data
        
    Inputs expected:
      - book_title
      - audience
      - goal
      - tone (Warm|Fun|Educational|Inspiring)
      - events (optional)
      - themes (optional)
      - age_range (optional, e.g., "ages 4–8")
      - differentiator (optional: what makes this book unique)
    """
    
    # Validate inputs
    if not inputs or not inputs.get('book_title'):
        logging.error("Missing required input: book_title")
        raise ValueError("book_title is required for post generation")
    
    logging.info(f"Starting post generation for '{inputs.get('book_title')}'")
    logging.debug(f"Generation parameters: num_days={num_days}, holidays={len(holidays) if holidays else 0}")
    
    # Format holidays for inclusion in prompt
    holiday_info = ""
    if holidays:
        try:
            from holidays import format_holidays_for_ai
            holiday_info = f"\n- {format_holidays_for_ai(holidays)}\n"
            logging.debug(f"Formatted holiday information: {len(holidays)} holidays")
        except Exception as holiday_format_error:
            logging.warning(f"Error formatting holidays: {str(holiday_format_error)}")
            holiday_info = ""
    
    # Build additional context section if provided
    additional_info = ""
    if inputs.get('additional_context'):
        additional_info = f"\n- Additional context: {inputs.get('additional_context')}"
    
    user_prompt = f"""Author/book context:
- Title: {inputs.get('book_title', '')}
- Primary audience: {inputs.get('audience', 'families, educators, authors')}
- Reader age range: {inputs.get('age_range', 'ages 4–8')}
- Monthly goal: {inputs.get('goal', 'grow newsletter + drive gentle sales')}
- Tone: {inputs.get('tone', 'Warm')}
- Events/Promos this month: {inputs.get('events', '(none)')}
- Themes to emphasize: {inputs.get('themes', 'courage, kindness, friendship')}
- Differentiator/Unique angle: {inputs.get('differentiator', '')}{holiday_info}{additional_info}

Requirements:
- Produce exactly {num_days} posts following the distribution rules and JSON schema.
- For QUOTE posts, invent a short, plausible line if no text supplied; keep it universal and on-brand.
- For PROMO posts, rotate CTAs: preorder link, launch team invite, review ask, school/library visit inquiry, newsletter.
- Hashtags: 3–6 per post, always include 1–2 broad kidlit tags plus 1–3 specific tags (topic/season/setting/age).
- Image ideas: concrete props/scene ideas (book + cozy chair; character plush; classroom anchor chart; shelfie at library).
- Hooks: varied patterns (question, startling fact, benefit-led, story-led). Max 70 chars.

Return JSON only.
"""

    try:
        # Use a faster model for reliability
        model = os.environ.get("OPENAI_MVP_MODEL", "gpt-4o-mini")
        
        logging.info(f"Calling OpenAI API with model: {model}")
        
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_KIDLIT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            max_tokens=6000  # Increased for 30 full posts with CTAs
        )
        
        raw_content = response.choices[0].message.content
        if not raw_content:
            raise ValueError("OpenAI returned empty content")
        raw_content = raw_content.strip()
        logging.debug(f"Received response from OpenAI: {len(raw_content)} chars")
        
        # Parse JSON response
        posts = json.loads(raw_content)
        
        if not isinstance(posts, list):
            raise ValueError("Expected a list of posts from OpenAI")
        
        # Validate we got exactly 30 posts
        if len(posts) < num_days:
            logging.warning(f"OpenAI generated only {len(posts)} posts instead of {num_days}. Padding with additional promo posts...")
            # Count theme distribution
            theme_counts = {}
            for post in posts:
                theme = post.get('theme', 'unknown')
                theme_counts[theme] = theme_counts.get(theme, 0) + 1
            
            # Add missing posts with varied CTAs
            cta_templates = [
                "Preorder your copy now [link]",
                "Join our launch team [link]",
                "Sign up for exclusive updates [link]",
                "Request a review copy [link]",
                "Link in bio",
                "Comment below",
                "Save this post for later",
                "Tag a friend who needs this",
                "Email me for details [link]",
                "Visit our website [link]"
            ]
            
            theme_options = ['promo', 'engagement', 'value']
            
            while len(posts) < num_days:
                theme = theme_options[len(posts) % len(theme_options)]
                cta = cta_templates[len(posts) % len(cta_templates)]
                
                if theme == 'engagement':
                    padded_post = {
                        "theme": "engagement",
                        "caption": f"What are your thoughts on '{inputs.get('book_title', 'this book')}'? Share your favorite moments and connect with other readers who love meaningful children's literature.",
                        "hashtags": "#KidLit #BookCommunity #ChildrensBooks #ReadersConnect",
                        "image_idea": "Community of readers sharing books and stories.",
                        "hook": "Join the conversation!",
                        "cta": cta
                    }
                elif theme == 'value':
                    padded_post = {
                        "theme": "value",
                        "caption": f"Looking for ways to discuss {inputs.get('themes', 'important topics')} with children? '{inputs.get('book_title', 'This book')}' offers gentle guidance for families and educators.",
                        "hashtags": "#KidLit #ParentingTips #EducationalBooks #SEL",
                        "image_idea": "Parent and child having a meaningful conversation with book nearby.",
                        "hook": "Meaningful conversations start here",
                        "cta": cta
                    }
                else:  # promo
                    padded_post = {
                        "theme": "promo",
                        "caption": f"Don't miss '{inputs.get('book_title', 'this book')}'! Join families and educators discovering how to navigate {inputs.get('themes', 'important themes')} with children.",
                        "hashtags": "#KidLit #PictureBook #ChildrensBooks #NewRelease",
                        "image_idea": "Book cover with promotional graphics.",
                        "hook": f"Ready to discover {inputs.get('book_title', 'this story')}?",
                        "cta": cta
                    }
                posts.append(padded_post)
                
        elif len(posts) > num_days:
            logging.warning(f"OpenAI generated {len(posts)} posts, trimming to {num_days}")
            posts = posts[:num_days]
        
        logging.info(f"Successfully generated {len(posts)} posts using OpenAI")
        return posts
        
    except Exception as e:
        logging.error(f"Error generating posts with OpenAI: {str(e)}")
        # Fallback to template-based generation
        logging.warning("Using fallback content generation due to API error")
        from fallback_posts import generate_fallback_posts
        return generate_fallback_posts(inputs, num_days, holidays)
